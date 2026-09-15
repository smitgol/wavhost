"""Voice library management for local TTS voice creation and storage."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Optional

from wavhost.config import BUFFER_SIZE, HASH_ALGORITHM, get_default_storage_path
from wavhost.exceptions import WavhostError
from wavhost.logging_config import get_logger

logger = get_logger(__name__)


class VoiceError(WavhostError):
    """Voice-related errors."""
    
    def __init__(self, message: str):
        super().__init__(message)


class VoiceNotFoundError(VoiceError):
    """Voice not found in storage."""
    
    def __init__(self, voice_name: str):
        super().__init__(f"Voice '{voice_name}' not found")
        self.voice_name = voice_name


class VoiceAlreadyExistsError(VoiceError):
    """Voice already exists in storage."""
    
    def __init__(self, voice_name: str):
        super().__init__(f"Voice '{voice_name}' already exists")
        self.voice_name = voice_name


class VoiceStorage:
    """Manages local voice library storage.
    
    Storage layout:
        ~/.wavhost/
            voices/
                manifests/
                    <voice_name>.json
                blobs/
                    sha256-<hash>
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize voice storage.
        
        Args:
            base_path: Base storage directory (defaults to ~/.wavhost)
        """
        self.base_path = base_path or get_default_storage_path()
        self.voices_path = self.base_path / "voices"
        self.manifests_path = self.voices_path / "manifests"
        self.blobs_path = self.voices_path / "blobs"
        
        self._ensure_directories()
        logger.debug(f"Voice storage initialized at {self.voices_path}")
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        try:
            self.manifests_path.mkdir(parents=True, exist_ok=True)
            self.blobs_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise VoiceError(f"Failed to create voice directories: {e}")
    
    def _compute_hash(self, file_path: Path) -> str:
        """Compute hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal hash digest
            
        Raises:
            VoiceError: If file cannot be read
        """
        try:
            hash_obj = hashlib.new(HASH_ALGORITHM)
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except (OSError, IOError) as e:
            raise VoiceError(f"Failed to compute hash for {file_path}: {e}")
    
    def _validate_voice_name(self, name: str) -> None:
        """Validate voice name.
        
        Args:
            name: Voice name
            
        Raises:
            VoiceError: If name is invalid
        """
        if not name or not name.strip():
            raise VoiceError("Voice name cannot be empty")
        
        if "/" in name or "\\" in name or ".." in name:
            raise VoiceError(
                f"Invalid voice name '{name}': cannot contain path separators"
            )
        
        if name.startswith("."):
            raise VoiceError(f"Invalid voice name '{name}': cannot start with '.'")
    
    def create_voice(
        self,
        name: str,
        ref_audio_path: Path,
        description: Optional[str] = None,
        backend: str = "chatterbox",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a new voice from reference audio.
        
        Args:
            name: Voice name (user-facing identifier)
            ref_audio_path: Path to reference audio file
            description: Optional voice description
            backend: Backend that will use this voice (default: chatterbox)
            metadata: Optional additional metadata
            
        Returns:
            Voice manifest dictionary
            
        Raises:
            VoiceAlreadyExistsError: If voice already exists
            VoiceError: If creation fails
        """
        self._validate_voice_name(name)
        
        if self.voice_exists(name):
            raise VoiceAlreadyExistsError(name)
        
        if not ref_audio_path.exists():
            raise VoiceError(f"Reference audio not found: {ref_audio_path}")
        
        # Store reference audio as content-addressed blob
        digest = self._compute_hash(ref_audio_path)
        blob_path = self._get_blob_path(digest)
        
        if not blob_path.exists():
            logger.info(f"Storing reference audio: {digest[:12]}...")
            try:
                shutil.copy2(ref_audio_path, blob_path)
            except OSError as e:
                raise VoiceError(f"Failed to store reference audio: {e}")
        else:
            logger.debug(f"Reference audio already exists: {digest[:12]}...")
        
        # Create voice manifest
        manifest = {
            "name": name,
            "description": description or "",
            "backend": backend,
            "ref_audio": {
                "digest": digest,
                "original_filename": ref_audio_path.name,
                "size": ref_audio_path.stat().st_size,
            },
            "metadata": metadata or {},
        }
        
        self._save_manifest(name, manifest)
        logger.info(f"Created voice: {name}")
        
        return manifest
    
    def get_voice(self, name: str) -> dict[str, Any]:
        """Get voice manifest by name.
        
        Args:
            name: Voice name
            
        Returns:
            Voice manifest dictionary
            
        Raises:
            VoiceNotFoundError: If voice doesn't exist
        """
        self._validate_voice_name(name)
        
        manifest = self._load_manifest(name)
        if manifest is None:
            raise VoiceNotFoundError(name)
        
        return manifest
    
    def get_voice_ref_audio_path(self, name: str) -> Path:
        """Get path to reference audio for a voice.
        
        Args:
            name: Voice name
            
        Returns:
            Path to reference audio blob
            
        Raises:
            VoiceNotFoundError: If voice doesn't exist
            VoiceError: If reference audio blob is missing
        """
        manifest = self.get_voice(name)
        digest = manifest["ref_audio"]["digest"]
        blob_path = self._get_blob_path(digest)
        
        if not blob_path.exists():
            raise VoiceError(
                f"Reference audio blob missing for voice '{name}': {digest[:12]}..."
            )
        
        return blob_path
    
    def list_voices(self) -> list[dict[str, Any]]:
        """List all voices in storage.
        
        Returns:
            List of voice manifests
        """
        voices = []
        
        if not self.manifests_path.exists():
            return voices
        
        try:
            for manifest_file in self.manifests_path.glob("*.json"):
                try:
                    manifest = self._load_manifest(manifest_file.stem)
                    if manifest:
                        voices.append(manifest)
                except Exception as e:
                    logger.warning(f"Failed to load manifest {manifest_file}: {e}")
                    continue
            
            return sorted(voices, key=lambda v: v["name"])
        except OSError as e:
            logger.error(f"Error listing voices: {e}")
            return voices
    
    def voice_exists(self, name: str) -> bool:
        """Check if a voice exists.
        
        Args:
            name: Voice name
            
        Returns:
            True if voice exists, False otherwise
        """
        try:
            self._validate_voice_name(name)
            return self._get_manifest_path(name).exists()
        except VoiceError:
            return False
    
    def delete_voice(self, name: str) -> bool:
        """Delete a voice and its reference audio if unused.
        
        Args:
            name: Voice name
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            VoiceError: If deletion fails
        """
        self._validate_voice_name(name)
        
        manifest_path = self._get_manifest_path(name)
        if not manifest_path.exists():
            return False
        
        try:
            # Load manifest to get blob digest
            manifest = self._load_manifest(name)
            digest = None
            if manifest and "ref_audio" in manifest:
                digest = manifest["ref_audio"].get("digest")
            
            # Delete manifest
            manifest_path.unlink()
            logger.info(f"Deleted voice: {name}")
            
            # Prune blob if no other voice references it
            if digest:
                if not self._blob_is_referenced(digest):
                    blob_path = self._get_blob_path(digest)
                    if blob_path.exists():
                        blob_path.unlink()
                        logger.info(f"Pruned unused blob: {digest[:12]}...")
            
            return True
            
        except OSError as e:
            raise VoiceError(f"Failed to delete voice: {e}")
    
    def _get_manifest_path(self, name: str) -> Path:
        """Get path to a voice manifest file.
        
        Args:
            name: Voice name
            
        Returns:
            Path to manifest file
        """
        return self.manifests_path / f"{name}.json"
    
    def _get_blob_path(self, digest: str) -> Path:
        """Get path to a blob by its digest.
        
        Args:
            digest: Hash digest
            
        Returns:
            Path to the blob file
        """
        return self.blobs_path / f"{HASH_ALGORITHM}-{digest}"
    
    def _save_manifest(self, name: str, manifest: dict[str, Any]) -> None:
        """Save a voice manifest.
        
        Args:
            name: Voice name
            manifest: Manifest data
            
        Raises:
            VoiceError: If save operation fails
        """
        try:
            manifest_path = self._get_manifest_path(name)
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            logger.debug(f"Saved voice manifest: {name}")
        except (OSError, IOError, json.JSONDecodeError) as e:
            raise VoiceError(f"Failed to save voice manifest: {e}")
    
    def _load_manifest(self, name: str) -> Optional[dict[str, Any]]:
        """Load a voice manifest.
        
        Args:
            name: Voice name
            
        Returns:
            Manifest data or None if not found
            
        Raises:
            VoiceError: If load operation fails
        """
        manifest_path = self._get_manifest_path(name)
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except (OSError, IOError, json.JSONDecodeError) as e:
            raise VoiceError(f"Failed to load voice manifest: {e}")
    
    def _blob_is_referenced(self, digest: str) -> bool:
        """Check if a blob is referenced by any voice.
        
        Args:
            digest: Blob digest
            
        Returns:
            True if any voice references this blob
        """
        for voice in self.list_voices():
            if voice.get("ref_audio", {}).get("digest") == digest:
                return True
        return False


def resolve_voice(
    voice: Optional[str],
    voice_storage: VoiceStorage,
) -> tuple[Optional[str], Optional[dict[str, str]]]:
    """Map a CLI/API voice string to ``(voice_arg, voice_handle)``.

    Order: saved library → existing file path → named speaker / opaque string.
    ``None`` / ``\"default\"`` means model built-in.
    """
    if voice is None or voice.lower() in {"", "default"}:
        return None, None

    if voice_storage.voice_exists(voice):
        return None, {
            "ref_audio_path": str(voice_storage.get_voice_ref_audio_path(voice))
        }

    path = Path(voice)
    if path.exists():
        return str(path), None

    return voice, None
