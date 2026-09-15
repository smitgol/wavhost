"""Command-line interface for Wavhost."""

import sys
from pathlib import Path
from typing import NoReturn, Optional

import click
import torch

from wavhost import dependencies
from wavhost.audio import save_wav
from wavhost.backends import create_backend
from wavhost.config import (
    DEFAULT_HOST,
    DEFAULT_OUTPUT_FILENAME,
    DEFAULT_PORT,
    VERSION,
)
from wavhost.exceptions import (
    BackendError,
    ModelNotFoundError,
    ModelNotInstalledError,
    WavhostError,
)
from wavhost.logging_config import setup_logger
from wavhost.registry import ModelRegistry
from wavhost.storage import WavhostStorage
from wavhost.voices import (
    VoiceAlreadyExistsError,
    VoiceNotFoundError,
    VoiceStorage,
    resolve_voice,
)

logger = setup_logger(__name__)


def handle_error(error: Exception, exit_code: int = 1) -> NoReturn:
    """Handle errors consistently across CLI commands.
    
    Args:
        error: Exception to handle
        exit_code: Exit code to use
    """
    if isinstance(error, WavhostError):
        click.echo(f"Error: {error}", err=True)
    else:
        click.echo(f"Unexpected error: {error}", err=True)
        logger.exception("Unexpected error occurred")
    
    sys.exit(exit_code)


def display_available_models(registry: ModelRegistry) -> None:
    click.echo("\nAvailable models:")
    for name in registry.list_models():
        info = registry.get_model_info(name)
        click.echo(f"  {name:<24} - {info.description}")


@click.group()
@click.version_option(version=VERSION, prog_name="wavhost")
def main():
    """Wavhost - Local-first TTS runtime.
    
    A local TTS runtime with OpenAI-compatible API.
    """
    pass


@main.command()
@click.argument("model_name")
@click.option("--force", is_flag=True, help="Pull even if the model is already installed (still resumes existing blobs)")
@click.option(
    "--skip-deps",
    is_flag=True,
    help="Don't install the backend engine (assume it's already available)"
)
def pull(model_name: str, force: bool, skip_deps: bool) -> None:
    """Pull a model from the registry.
    
    Displays license terms, installs the backend engine if needed, and
    downloads weight layers into local storage.
    
    Example: wavhost pull chatterbox-turbo
    """
    try:
        registry = ModelRegistry()
        storage = WavhostStorage()
        
        model_info = registry.get_model_info(model_name)
        
        already_pulled = (
            storage.manifest_exists(model_info.namespace, model_info.name, model_info.tag)
            and not force
        )
        
        if not already_pulled:
            click.echo(registry.format_license_display(model_name))
            click.echo()
            
            if not click.confirm("Do you accept the license terms?", default=True):
                click.echo("License not accepted. Aborting.")
                sys.exit(0)
        
        # The manifest lives in shared storage, but the engine is installed per
        # interpreter, so an existing manifest says nothing about whether this
        # Python can actually run the model.
        if not skip_deps:
            _ensure_backend_installed(model_info.backend)
        
        # Installing the engine may have swapped a CUDA torch for the CPU
        # wheel PyPI serves for its exact pin. Say so now, with the fix, rather
        # than letting the user discover it as a slow first synthesis.
        _warn_if_cpu_torch()
        
        if already_pulled:
            click.echo(f"Model '{model_name}' is already installed.")
            click.echo("Use --force to re-download.")
            return
        
        _pull_model(storage, model_info, force=force)
        
        click.echo(f"\n✓ Model installed: {model_info.full_name}")
        click.echo(f"\nRun with: wavhost run {model_name} 'Hello world'")
        
    except ModelNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        display_available_models(registry)
        sys.exit(1)
    except Exception as e:
        handle_error(e)


def _ensure_backend_installed(backend: str) -> None:
    """Install the engine a backend needs, prompting before doing so.
    
    Args:
        backend: Backend identifier from the model info
        
    Raises:
        BackendError: If installation fails
    """
    requirement = dependencies.get_requirement(backend)
    
    if requirement is None or dependencies.is_installed(backend):
        return
    
    click.echo(f"The '{backend}' backend engine is not installed yet.")
    click.echo(f"Packages to install: {', '.join(requirement.packages)}")
    click.echo(f"Target interpreter: {sys.executable}")
    click.echo("This may download several hundred MB and take a few minutes.")
    click.echo()
    
    if not click.confirm(f"Install the {backend} engine now?", default=True):
        click.echo("Aborting. Install it yourself with:")
        click.echo(f"  {dependencies.install_hint(backend)}")
        click.echo("Then re-run with --skip-deps.")
        sys.exit(0)
    
    click.echo()
    dependencies.install(backend)
    click.echo(f"\n✓ {backend} engine installed")


def _warn_if_cpu_torch() -> None:
    """Warn when an NVIDIA GPU exists but torch is a CPU-only build."""
    warning = dependencies.gpu_build_warning()
    if warning:
        click.echo()
        click.echo(f"Warning: {warning}", err=True)
        click.echo()


def _pull_model(storage: WavhostStorage, model_info, *, force: bool = False) -> None:
    """Download model layers into storage and write the manifest.
    
    Args:
        storage: Storage instance
        model_info: Model information
        force: Re-download layers even when blobs exist
    """
    click.echo(f"\nPulling model: {model_info.name}")
    click.echo(f"Backend: {model_info.backend}")
    click.echo(f"Description: {model_info.description}")
    click.echo(f"Layers: {len(model_info.layers)}")
    click.echo()
    
    if not model_info.layers:
        raise BackendError(
            f"Model '{model_info.name}' has no downloadable layers declared"
        )
    
    storage.pull_layers(model_info, force=force, show_progress=True)


@main.command()
@click.argument("model_name")
@click.argument("text")
@click.option("-o", "--output", type=click.Path(), help="Output WAV file path")
@click.option(
    "--voice",
    type=str,
    help=(
        "Saved voice name, reference audio path, or Qwen CustomVoice speaker "
        "(Ryan, Aiden, Vivian, ...). Omit for the model default."
    ),
)
@click.option(
    "--language",
    "-l",
    type=str,
    default=None,
    help=(
        "Language for synthesis. Chatterbox Multilingual: ISO code "
        "(en, fr, zh, …). Qwen: English, Chinese, …"
    ),
)
@click.option("--device", type=str, help="Device to use (cuda/cpu/mps)")
def run(
    model_name: str,
    text: str,
    output: Optional[str],
    voice: Optional[str],
    language: Optional[str],
    device: Optional[str],
) -> None:
    """Generate speech from text using a model.
    
    Example: wavhost run chatterbox-turbo "Hello world" -o output.wav
    """
    try:
        storage = WavhostStorage()
        registry = ModelRegistry()
        voice_storage = VoiceStorage()

        model_info = registry.get_model_info(model_name)
        checkpoint = storage.ensure_checkpoint(model_info)
        voice_arg, voice_handle = resolve_voice(voice, voice_storage)
        if voice_handle:
            click.echo(f"Using saved voice: {voice}")
        elif voice_arg and not Path(voice_arg).exists():
            click.echo(f"Using speaker: {voice_arg}")
        if language:
            click.echo(f"Language: {language}")

        _generate_speech(
            model_info,
            text,
            output,
            voice_arg,
            device,
            checkpoint,
            voice_handle,
            language=language,
        )
    except Exception as e:
        handle_error(e)


def _generate_speech(
    model_info,
    text: str,
    output: Optional[str],
    voice: Optional[str],
    device: Optional[str],
    checkpoint: Path,
    voice_handle: Optional[dict] = None,
    language: Optional[str] = None,
) -> None:
    click.echo(f"Loading model: {model_info.name}")

    if device == "cuda" and not torch.cuda.is_available():
        click.echo(
            "Warning: CUDA requested but not available, falling back to CPU",
            err=True,
        )
        device = "cpu"

    backend = create_backend(model_info, device=device, checkpoint_path=checkpoint)
    click.echo(f"Generating speech for: '{text}'")
    gen_kwargs = {}
    if language:
        gen_kwargs["language"] = language
    wav, sr = backend.generate(
        text, voice=voice, voice_handle=voice_handle, **gen_kwargs
    )
    out = save_wav(output or DEFAULT_OUTPUT_FILENAME, wav, sr)
    click.echo(f"Audio saved to: {out}")


@main.command()
@click.option("--host", default=DEFAULT_HOST, help="Host to bind to")
@click.option("--port", default=DEFAULT_PORT, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the OpenAI-compatible TTS server.
    
    Serves an OpenAI-compatible /v1/audio/speech endpoint.
    
    Example: wavhost serve --port 11435
    """
    try:
        import uvicorn
        
        _display_server_info(host, port)
        
        uvicorn.run(
            "wavhost.server:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except ImportError:
        click.echo("Error: uvicorn not installed. Install with: pip install uvicorn[standard]", err=True)
        sys.exit(1)
    except Exception as e:
        handle_error(e)


def _display_server_info(host: str, port: int) -> None:
    """Display server startup information.
    
    Args:
        host: Server host
        port: Server port
    """
    click.echo("Starting Wavhost server...")
    click.echo(f"OpenAI-compatible endpoint: http://{host}:{port}/v1/audio/speech")
    click.echo(f"\nExample curl command:")
    click.echo(f'curl http://{host}:{port}/v1/audio/speech \\')
    click.echo(f'  -H "Content-Type: application/json" \\')
    click.echo(f'  -d \'{{"model":"chatterbox-turbo","input":"Hello world","voice":"default"}}\' \\')
    click.echo(f'  --output speech.mp3')
    click.echo()


@main.command("list")
def list_models() -> None:
    """List installed models and available models in registry."""
    try:
        storage = WavhostStorage()
        registry = ModelRegistry()
        
        installed = storage.list_models()
        
        if installed:
            click.echo("Installed models:")
            for namespace, name, tag in installed:
                click.echo(f"  {namespace}/{name}:{tag}")
        else:
            click.echo("No models installed.")
        
        display_available_models(registry)
        
    except Exception as e:
        handle_error(e)


def _resolve_installed_model(
    storage: WavhostStorage,
    registry: ModelRegistry,
    model_name: str,
) -> tuple[str, str, str]:
    """Map a user-facing model name to an installed (namespace, name, tag).

    Prefers the registry definition when present; otherwise matches by name
    among installed manifests.
    """
    try:
        info = registry.get_model_info(model_name)
        if storage.manifest_exists(info.namespace, info.name, info.tag):
            return info.namespace, info.name, info.tag
        raise ModelNotInstalledError(model_name)
    except ModelNotFoundError:
        matches = [
            (ns, name, tag)
            for ns, name, tag in storage.list_models()
            if name == model_name or f"{ns}/{name}" == model_name
        ]
        if not matches:
            raise ModelNotInstalledError(model_name)
        if len(matches) > 1:
            listed = ", ".join(f"{ns}/{name}:{tag}" for ns, name, tag in matches)
            raise WavhostError(
                f"Ambiguous model '{model_name}' matches: {listed}. "
                f"Use a full name like '{matches[0][0]}/{matches[0][1]}'."
            )
        return matches[0]


@main.command("rm")
@click.argument("model_name")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def remove_model(model_name: str, yes: bool) -> None:
    """Remove a pulled model and free its disk space.

    Deletes the manifest, checkpoint, pull-state, and any blobs that no other
    installed model still uses.

    Example: wavhost rm chatterbox-turbo
    """
    try:
        storage = WavhostStorage()
        registry = ModelRegistry()
        namespace, name, tag = _resolve_installed_model(storage, registry, model_name)
        full = f"{namespace}/{name}:{tag}"

        if not yes and not click.confirm(f"Remove model {full}?", default=True):
            click.echo("Aborted.")
            return

        if not storage.delete_model(namespace, name, tag):
            raise ModelNotInstalledError(model_name)

        click.echo(f"✓ Removed {full}")
    except Exception as e:
        handle_error(e)


@main.command()
@click.option(
    "--purge-data/--keep-data",
    default=True,
    show_default=True,
    help="Delete ~/.wavhost (models, blobs, checkpoints)",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def uninstall(purge_data: bool, yes: bool) -> None:
    """Uninstall local Wavhost data (and show how to remove the package).

    By default this deletes the storage tree under ~/.wavhost so you can
    start fresh. The Python package itself is left to pip:

        pip uninstall wavhost

    Example: wavhost uninstall
    """
    try:
        storage = WavhostStorage()
        root = storage.base_path

        if purge_data:
            if not yes:
                click.echo(f"This will delete all local Wavhost data under:\n  {root}")
                click.echo()
                if not click.confirm("Continue?", default=False):
                    click.echo("Aborted.")
                    return

            storage.purge()
            click.echo(f"✓ Removed local data: {root}")
        else:
            click.echo(f"Kept local data at {root}")

        click.echo()
        click.echo("To remove the Wavhost package from this Python:")
        click.echo(f"  {sys.executable} -m pip uninstall wavhost")
        click.echo()
        click.echo("Optional — also remove backend engines:")
        click.echo(f"  {sys.executable} -m pip uninstall chatterbox-tts")
        click.echo(f"  {sys.executable} -m pip uninstall qwen-tts")
    except Exception as e:
        handle_error(e)


# Voice management commands
@main.group()
def voice():
    """Manage local voice library.
    
    Create, list, and manage saved voices for TTS generation.
    """
    pass


@voice.command("create")
@click.argument("name")
@click.option("--ref", type=click.Path(exists=True), required=True, help="Reference audio file")
@click.option("--desc", type=str, help="Voice description")
def voice_create(name: str, ref: str, desc: Optional[str]) -> None:
    """Create a new voice from reference audio.
    
    Example: wavhost voice create my-voice --ref audio.wav --desc "My custom voice"
    """
    try:
        voice_storage = VoiceStorage()
        ref_path = Path(ref)
        
        manifest = voice_storage.create_voice(
            name=name,
            ref_audio_path=ref_path,
            description=desc,
        )
        
        click.echo(f"✓ Created voice: {name}")
        if desc:
            click.echo(f"  Description: {desc}")
        click.echo(f"  Reference: {ref}")
        click.echo(f"\nUse with: wavhost run <model> 'text' --voice {name}")
        
    except VoiceAlreadyExistsError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo(f"Use a different name or remove the existing voice first.", err=True)
        sys.exit(1)
    except Exception as e:
        handle_error(e)


@voice.command("list")
def voice_list() -> None:
    """List all saved voices.
    
    Example: wavhost voice list
    """
    try:
        voice_storage = VoiceStorage()
        voices = voice_storage.list_voices()
        
        if not voices:
            click.echo("No voices saved yet.")
            click.echo("\nCreate one with: wavhost voice create <name> --ref <audio>")
            return
        
        click.echo(f"Saved voices ({len(voices)}):")
        for v in voices:
            name = v["name"]
            desc = v.get("description", "")
            backend = v.get("backend", "")
            click.echo(f"  {name:<20} - {desc if desc else f'({backend})'}")
        
    except Exception as e:
        handle_error(e)


@voice.command("show")
@click.argument("name")
def voice_show(name: str) -> None:
    """Show details about a saved voice.
    
    Example: wavhost voice show my-voice
    """
    try:
        voice_storage = VoiceStorage()
        manifest = voice_storage.get_voice(name)
        
        click.echo(f"Voice: {manifest['name']}")
        if manifest.get("description"):
            click.echo(f"Description: {manifest['description']}")
        click.echo(f"Backend: {manifest.get('backend', 'unknown')}")
        
        ref_info = manifest.get("ref_audio", {})
        if ref_info:
            click.echo(f"\nReference audio:")
            click.echo(f"  Original file: {ref_info.get('original_filename', 'unknown')}")
            click.echo(f"  Size: {ref_info.get('size', 0):,} bytes")
            click.echo(f"  Digest: {ref_info.get('digest', '')[:12]}...")
        
        metadata = manifest.get("metadata", {})
        if metadata:
            click.echo(f"\nMetadata: {metadata}")
        
    except VoiceNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo(f"\nList available voices with: wavhost voice list", err=True)
        sys.exit(1)
    except Exception as e:
        handle_error(e)


@voice.command("rm")
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def voice_remove(name: str, yes: bool) -> None:
    """Remove a saved voice.
    
    Example: wavhost voice rm my-voice
    """
    try:
        voice_storage = VoiceStorage()
        
        if not voice_storage.voice_exists(name):
            click.echo(f"Error: Voice '{name}' not found", err=True)
            sys.exit(1)
        
        if not yes and not click.confirm(f"Remove voice '{name}'?", default=True):
            click.echo("Aborted.")
            return
        
        if voice_storage.delete_voice(name):
            click.echo(f"✓ Removed voice: {name}")
        else:
            click.echo(f"Error: Voice '{name}' not found", err=True)
            sys.exit(1)
        
    except Exception as e:
        handle_error(e)


if __name__ == "__main__":
    main()