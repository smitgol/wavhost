"""Storage layer for Ollama-style content-addressed model storage."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Optional

from tqdm import tqdm

from wavhost.config import (
    BLOB_PREFIX,
    BLOBS_DIR_NAME,
    BUFFER_SIZE,
    HASH_ALGORITHM,
    get_blobs_path,
    get_checkpoints_path,
    get_default_storage_path,
    get_manifests_path,
    get_pull_state_path,
)
from wavhost.exceptions import StorageError
from wavhost.logging_config import get_logger

logger = get_logger(__name__)


class WavhostStorage:
    """Manages model storage in Ollama-style directory structure.
    
    Storage layout:
        ~/.wavhost/
            models/
                manifests/
                    registry/
                        <namespace>/
                            <model>/
                                <tag>
                blobs/
                    sha256-<hash>
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize storage manager.
        
        Args:
            base_path: Base storage directory (defaults to ~/.wavhost)
        """
        self.base_path = base_path or get_default_storage_path()
        self.manifests_path = get_manifests_path(self.base_path)
        self.blobs_path = get_blobs_path(self.base_path)
        self.checkpoints_path = get_checkpoints_path(self.base_path)
        self.pull_state_path = get_pull_state_path(self.base_path)
        
        self._ensure_directories()
        logger.debug(f"Storage initialized at {self.base_path}")
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        try:
            self.manifests_path.mkdir(parents=True, exist_ok=True)
            self.blobs_path.mkdir(parents=True, exist_ok=True)
            self.checkpoints_path.mkdir(parents=True, exist_ok=True)
            self.pull_state_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create storage directories: {e}")
    
    def _compute_hash(self, file_path: Path, show_progress: bool = True) -> str:
        """Compute hash of a file with optional progress bar.
        
        Args:
            file_path: Path to the file
            show_progress: Whether to show progress bar
            
        Returns:
            Hexadecimal hash digest
            
        Raises:
            StorageError: If file cannot be read
        """
        try:
            file_size = file_path.stat().st_size
            hash_obj = hashlib.new(HASH_ALGORITHM)
            
            with open(file_path, "rb") as f:
                progress_bar = (
                    tqdm(total=file_size, unit='B', unit_scale=True, desc="Hashing")
                    if show_progress else None
                )
                
                try:
                    for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
                        hash_obj.update(chunk)
                        if progress_bar is not None:
                            progress_bar.update(len(chunk))
                finally:
                    if progress_bar is not None:
                        progress_bar.close()
            
            return hash_obj.hexdigest()
            
        except (OSError, IOError) as e:
            raise StorageError(f"Failed to compute hash for {file_path}: {e}")
    
    def _copy_with_progress(
        self,
        src: Path,
        dst: Path,
        show_progress: bool = True
    ) -> None:
        """Copy file with optional progress bar.
        
        Args:
            src: Source file path
            dst: Destination file path
            show_progress: Whether to show progress bar
            
        Raises:
            StorageError: If copy fails
        """
        try:
            file_size = src.stat().st_size
            
            if show_progress:
                with tqdm(total=file_size, unit='B', unit_scale=True, desc="Copying") as pbar:
                    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
                        for chunk in iter(lambda: fsrc.read(BUFFER_SIZE), b""):
                            fdst.write(chunk)
                            pbar.update(len(chunk))
            else:
                shutil.copy2(src, dst)
                
        except (OSError, IOError) as e:
            raise StorageError(f"Failed to copy {src} to {dst}: {e}")
    
    def store_blob(self, file_path: Path, show_progress: bool = True) -> str:
        """Store a file as a content-addressed blob.
        
        Args:
            file_path: Path to the file to store
            show_progress: Whether to show progress bar
            
        Returns:
            Hash digest of the file
            
        Raises:
            StorageError: If storage operation fails
        """
        if not file_path.exists():
            raise StorageError(f"File not found: {file_path}")
        
        digest = self._compute_hash(file_path, show_progress)
        blob_path = self.get_blob_path(digest)
        
        if not blob_path.exists():
            logger.info(f"Storing blob: {digest[:12]}...")
            self._copy_with_progress(file_path, blob_path, show_progress)
        else:
            logger.debug(f"Blob already exists: {digest[:12]}...")
        
        return digest
    
    def get_blob_path(self, digest: str) -> Path:
        """Get the path to a blob by its digest.
        
        Args:
            digest: Hash digest
            
        Returns:
            Path to the blob file
        """
        return self.blobs_path / f"{BLOB_PREFIX}{digest}"
    
    def blob_exists(self, digest: str) -> bool:
        """Check if a blob exists.
        
        Args:
            digest: Hash digest
            
        Returns:
            True if blob exists, False otherwise
        """
        return self.get_blob_path(digest).exists()
    
    def _get_manifest_path(self, namespace: str, model: str, tag: str) -> Path:
        """Get the path to a manifest file.
        
        Args:
            namespace: Model namespace
            model: Model name
            tag: Model tag
            
        Returns:
            Path to manifest file
        """
        return self.manifests_path / namespace / model / tag
    
    def save_manifest(
        self,
        namespace: str,
        model: str,
        tag: str,
        manifest: dict[str, Any]
    ) -> None:
        """Save a model manifest.
        
        Args:
            namespace: Model namespace (e.g., 'resemble')
            model: Model name (e.g., 'chatterbox-turbo')
            tag: Model tag (e.g., 'latest')
            manifest: Manifest data
            
        Raises:
            StorageError: If save operation fails
        """
        try:
            manifest_path = self._get_manifest_path(namespace, model, tag)
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Saved manifest: {namespace}/{model}:{tag}")
            
        except (OSError, IOError, json.JSONDecodeError) as e:
            raise StorageError(f"Failed to save manifest: {e}")
    
    def load_manifest(
        self,
        namespace: str,
        model: str,
        tag: str
    ) -> Optional[dict[str, Any]]:
        """Load a model manifest.
        
        Args:
            namespace: Model namespace
            model: Model name
            tag: Model tag
            
        Returns:
            Manifest data or None if not found
            
        Raises:
            StorageError: If load operation fails (but not if file doesn't exist)
        """
        manifest_path = self._get_manifest_path(namespace, model, tag)
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except (OSError, IOError, json.JSONDecodeError) as e:
            raise StorageError(f"Failed to load manifest: {e}")
    
    def manifest_exists(self, namespace: str, model: str, tag: str) -> bool:
        """Check if a manifest exists.
        
        Args:
            namespace: Model namespace
            model: Model name
            tag: Model tag
            
        Returns:
            True if manifest exists, False otherwise
        """
        return self._get_manifest_path(namespace, model, tag).exists()
    
    def list_models(self) -> list[tuple[str, str, str]]:
        """List all installed models.
        
        Returns:
            Sorted list of (namespace, model, tag) tuples
        """
        models = []
        
        if not self.manifests_path.exists():
            return models
        
        try:
            for namespace_dir in self.manifests_path.iterdir():
                if not namespace_dir.is_dir():
                    continue
                    
                for model_dir in namespace_dir.iterdir():
                    if not model_dir.is_dir():
                        continue
                        
                    for tag_file in model_dir.iterdir():
                        if tag_file.is_file():
                            models.append((
                                namespace_dir.name,
                                model_dir.name,
                                tag_file.name
                            ))
            
            return sorted(models)
            
        except OSError as e:
            logger.error(f"Error listing models: {e}")
            return models
    
    def delete_model(
        self,
        namespace: str,
        model: str,
        tag: str,
        *,
        prune_blobs: bool = True,
    ) -> bool:
        """Delete an installed model (manifest, checkpoint, pull-state).

        By default, blobs that no other installed model still references are
        removed too so disk space is actually freed.

        Args:
            namespace: Model namespace
            model: Model name
            tag: Model tag
            prune_blobs: Drop unreferenced blobs after removing this model

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion fails
        """
        manifest_path = self._get_manifest_path(namespace, model, tag)

        if not manifest_path.exists():
            return False

        try:
            digests: set[str] = set()
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                for layer in manifest.get("layers") or []:
                    digest = layer.get("digest")
                    if digest:
                        digests.add(digest)
            except (OSError, json.JSONDecodeError):
                pass

            # Remove materialized checkpoint (hardlinks or copies).
            ckpt_dir = self.get_checkpoint_path(namespace, model, tag)
            if ckpt_dir.exists():
                shutil.rmtree(ckpt_dir, ignore_errors=True)
                self._rmdir_if_empty(ckpt_dir.parent)
                self._rmdir_if_empty(ckpt_dir.parent.parent)

            # Drop durable pull-resume state for this model.
            state_path = self.pull_state_path / f"{namespace}__{model}.json"
            if state_path.exists():
                state_path.unlink(missing_ok=True)

            # Drop any leftover tmp download dir for this model name.
            tmp_dir = self.base_path / "tmp" / model
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

            manifest_path.unlink()
            logger.info(f"Deleted model: {namespace}/{model}:{tag}")

            model_dir = manifest_path.parent
            self._rmdir_if_empty(model_dir)
            self._rmdir_if_empty(model_dir.parent)

            if prune_blobs and digests:
                still_used = self._referenced_digests()
                for digest in digests:
                    if digest not in still_used:
                        blob_path = self.get_blob_path(digest)
                        if blob_path.exists():
                            blob_path.unlink()
                            logger.info(f"Pruned unused blob {digest[:12]}...")

            return True

        except OSError as e:
            raise StorageError(f"Failed to delete model: {e}")

    def _rmdir_if_empty(self, path: Path) -> None:
        """Remove a directory when it exists and has no children."""
        try:
            if path.exists() and path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        except OSError:
            pass

    def _referenced_digests(self) -> set[str]:
        """Collect every blob digest still named by an installed manifest."""
        digests: set[str] = set()
        for namespace, model, tag in self.list_models():
            manifest = self.load_manifest(namespace, model, tag)
            if not manifest:
                continue
            for layer in manifest.get("layers") or []:
                digest = layer.get("digest")
                if digest:
                    digests.add(digest)
        return digests

    def purge(self) -> Path:
        """Delete the entire Wavhost storage tree (models, blobs, state).

        Recreates the empty directory layout afterward so later commands can
        run without an explicit re-init.

        Returns:
            The storage root that was wiped

        Raises:
            StorageError: If the tree cannot be removed
        """
        root = self.base_path
        try:
            if root.exists():
                shutil.rmtree(root)
            self._ensure_directories()
            logger.info(f"Purged storage at {root}")
            return root
        except OSError as e:
            raise StorageError(f"Failed to purge storage at {root}: {e}")

    def get_checkpoint_path(self, namespace: str, model: str, tag: str) -> Path:
        """Path to the materialized checkpoint directory for a model."""
        return self.checkpoints_path / namespace / model / tag

    def store_file_as_blob(self, file_path: Path, digest: Optional[str] = None) -> str:
        """Move or copy a downloaded file into content-addressed blob storage.

        Args:
            file_path: Local file to store
            digest: Precomputed digest; computed if omitted

        Returns:
            Digest of the stored blob
        """
        if not file_path.exists():
            raise StorageError(f"File not found: {file_path}")

        digest = digest or self._compute_hash(file_path, show_progress=False)
        blob_path = self.get_blob_path(digest)

        if blob_path.exists():
            file_path.unlink(missing_ok=True)
            return digest

        try:
            file_path.replace(blob_path)
        except OSError:
            self._copy_with_progress(file_path, blob_path, show_progress=False)
            file_path.unlink(missing_ok=True)

        return digest

    def materialize_checkpoint(
        self,
        namespace: str,
        model: str,
        tag: str,
        layers: list[dict[str, Any]],
    ) -> Path:
        """Link or copy blobs into a checkpoint directory with expected filenames.

        Args:
            namespace: Model namespace
            model: Model name
            tag: Model tag
            layers: Manifest layer entries with filename + digest

        Returns:
            Path to the checkpoint directory

        Raises:
            StorageError: If a blob is missing or linking fails
        """
        ckpt_dir = self.get_checkpoint_path(namespace, model, tag)
        try:
            ckpt_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create checkpoint dir: {e}")

        for layer in layers:
            filename = layer["filename"]
            digest = layer["digest"]
            blob_path = self.get_blob_path(digest)
            if not blob_path.exists():
                raise StorageError(
                    f"Missing blob {digest[:12]}... for layer {filename}"
                )

            target = ckpt_dir / filename
            if target.exists():
                try:
                    if target.samefile(blob_path):
                        continue
                except OSError:
                    pass
                target.unlink()

            try:
                target.hardlink_to(blob_path)
            except OSError:
                try:
                    self._copy_with_progress(blob_path, target, show_progress=False)
                except StorageError as e:
                    raise StorageError(
                        f"Failed to materialize {filename}: {e}"
                    ) from e

        return ckpt_dir

    def checkpoint_ready(
        self,
        namespace: str,
        model: str,
        tag: str,
        layers: list[dict[str, Any]],
    ) -> bool:
        """True if every layer file exists in the checkpoint directory."""
        ckpt_dir = self.get_checkpoint_path(namespace, model, tag)
        if not ckpt_dir.exists():
            return False
        return all((ckpt_dir / layer["filename"]).exists() for layer in layers)

    def pull_layers(
        self,
        model_info: Any,
        *,
        force: bool = False,
        show_progress: bool = True,
    ) -> dict[str, Any]:
        """Download model layers into blobs and write a full manifest.

        Progress is checkpointed after each layer so a failed pull can resume
        without re-downloading multi-GB files that already landed in blobs.

        Args:
            model_info: Registry ModelInfo with layers
            force: Re-download even when blobs already exist
            show_progress: Show download progress bars

        Returns:
            The written manifest dictionary
        """
        from wavhost.download import download_file

        layer_entries: list[dict[str, Any]] = []
        tmp_dir = self.base_path / "tmp" / model_info.name
        tmp_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.pull_state_path / f"{model_info.namespace}__{model_info.name}.json"
        # Migrate legacy tmp pull-state if present.
        legacy_state = tmp_dir / "pull-state.json"
        if not state_path.exists() and legacy_state.exists():
            try:
                state_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy_state, state_path)
            except OSError:
                pass

        # Always resume from pull-state. `--force` only means "pull even if a
        # finished manifest already exists" at the CLI layer — it must not wipe
        # multi-GB blobs the user already paid to download.
        prior = self._load_pull_state(state_path)

        try:
            for layer in model_info.layers:
                dest = tmp_dir / layer.filename
                blob_digest = layer.sha256
                prior_entry = prior.get(layer.filename) or {}
                prior_digest = prior_entry.get("digest") or blob_digest

                if prior_digest and self.blob_exists(prior_digest):
                    digest = prior_digest
                    size = self.get_blob_path(digest).stat().st_size
                    logger.info(f"Skipping {layer.filename} (already in blobs)")
                    if show_progress:
                        print(f"Skipping {layer.filename} (already downloaded)")
                else:
                    digest = download_file(
                        layer.url,
                        dest,
                        expected_sha256=layer.sha256,
                        show_progress=show_progress,
                    )
                    if not dest.exists() and self.blob_exists(digest):
                        pass
                    elif dest.exists():
                        digest = self.store_file_as_blob(dest, digest=digest)
                    else:
                        raise StorageError(
                            f"Download of {layer.filename} did not produce a file"
                        )
                    size = self.get_blob_path(digest).stat().st_size

                entry = {
                    "filename": layer.filename,
                    "url": layer.url,
                    "digest": digest,
                    "size": size,
                }
                layer_entries.append(entry)
                prior[layer.filename] = entry
                self._save_pull_state(state_path, prior)

            ckpt_dir = self.materialize_checkpoint(
                model_info.namespace,
                model_info.name,
                model_info.tag,
                layer_entries,
            )

            manifest = {
                "model_name": model_info.name,
                "namespace": model_info.namespace,
                "name": model_info.name,
                "tag": model_info.tag,
                "backend": model_info.backend,
                "model_class": model_info.model_class,
                "checkpoint_path": str(ckpt_dir),
                "layers": layer_entries,
                "model_info": model_info.to_dict(),
            }

            self.save_manifest(
                model_info.namespace,
                model_info.name,
                model_info.tag,
                manifest,
            )
            # Successful pull — drop staging temps and resume state.
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
            state_path.unlink(missing_ok=True)
            return manifest
        except Exception:
            # Keep tmp_dir + pull-state so the next pull resumes.
            raise

    def _load_pull_state(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            raw = path.read_text(encoding="utf-8-sig").strip()
            if not raw:
                logger.warning(f"Ignoring empty pull state {path}")
                return {}
            data = json.loads(raw)
            layers = data.get("layers", data)
            return layers if isinstance(layers, dict) else {}
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Ignoring corrupt pull state {path}: {e}")
            return {}

    def _save_pull_state(self, path: Path, layers: dict[str, Any]) -> None:
        """Atomically write pull-state so Ctrl+C cannot leave an empty JSON file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps({"layers": layers}, indent=2)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(path)
        except OSError as e:
            logger.warning(f"Failed to save pull state: {e}")
