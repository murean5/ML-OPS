"""Сервис для работы с DVC."""

import os
import subprocess
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


class DVCService:
    """Сервис для версионирования датасетов через DVC."""

    def __init__(self):
        """Инициализация сервиса."""
        self.remote = settings.dvc_remote
        self._init_dvc()
        self._setup_dvc_remote()
        logger.info("Инициализирован DVCService")
    
    def _init_dvc(self):
        """Инициализировать DVC если еще не инициализирован."""
        try:
            if not os.path.exists(".dvc"):
                subprocess.run(
                    ["dvc", "init", "--no-scm"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                gitignore_path = ".gitignore"
                if os.path.exists(gitignore_path):
                    with open(gitignore_path, "r") as f:
                        lines = f.readlines()
                    modified = False
                    new_lines = []
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped == "data/":
                            new_lines.append("data/*.csv\n")
                            new_lines.append("!data/*.csv.dvc\n")
                            modified = True
                        elif stripped.startswith("data/") and "*.csv" not in stripped:
                            new_lines.append("data/*.csv\n")
                            new_lines.append("!data/*.csv.dvc\n")
                            modified = True
                        else:
                            new_lines.append(line)
                    if modified:
                        with open(gitignore_path, "w") as f:
                            f.writelines(new_lines)
                        logger.info("Обновлен .gitignore для поддержки DVC")
                logger.info("DVC инициализирован")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать DVC: {e}")
    
    def _setup_dvc_remote(self):
        """Настроить DVC remote для MinIO."""
        try:
            result = subprocess.run(
                ["dvc", "remote", "list"],
                capture_output=True,
                text=True,
            )
            endpoint = settings.minio_endpoint
            endpoint = endpoint.replace('http://', '').replace('https://', '')
            
            if self.remote not in result.stdout:
                subprocess.run(
                    ["dvc", "remote", "add", self.remote, f"s3://dvc-storage"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                subprocess.run(
                    ["dvc", "remote", "default", self.remote],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            
            subprocess.run(
                ["dvc", "remote", "modify", self.remote, "endpointurl", f"http://{endpoint}"],
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["dvc", "remote", "modify", self.remote, "access_key_id", settings.minio_access_key],
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["dvc", "remote", "modify", self.remote, "secret_access_key", settings.minio_secret_key],
                capture_output=True,
                text=True,
                check=False,
            )
            logger.info(f"DVC remote '{self.remote}' настроен для MinIO (endpoint: {endpoint})")
        except Exception as e:
            logger.warning(f"Не удалось настроить DVC remote: {e}")

    def add_dataset(self, filepath: str, file_name: str) -> Optional[str]:
        """
        Добавить датасет в DVC.

        Args:
            filepath: Путь к файлу датасета
            file_name: Имя файла

        Returns:
            Версия датасета в DVC или None
        """
        try:
            result = subprocess.run(
                ["dvc", "add", filepath],
                capture_output=True,
                text=True,
                check=True,
            )

            try:
                subprocess.run(
                    ["git", "add", f"{filepath}.dvc"],
                    capture_output=True,
                    check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            logger.info(f"Датасет добавлен в DVC")

            try:
                dvc_file = f"{filepath}.dvc"
                if os.path.exists(dvc_file):
                    import yaml
                    with open(dvc_file, "r") as f:
                        dvc_data = yaml.safe_load(f)
                        if dvc_data and "outs" in dvc_data and len(dvc_data["outs"]) > 0:
                            md5_hash = dvc_data["outs"][0].get("md5", "")
                            if md5_hash:
                                return md5_hash[:16]
            except Exception:
                pass
            return None

        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при добавлении датасета в DVC: {str(e)} (filepath: {filepath})")
            return None

    def push_dataset(self, filepath: str) -> bool:
        """
        Отправить датасет в удаленное хранилище (S3/MinIO).

        Args:
            filepath: Путь к файлу датасета

        Returns:
            True если успешно, False иначе
        """
        try:
            result = subprocess.run(
                ["dvc", "push", "-r", self.remote, filepath],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Датасет отправлен в S3 (MinIO) через DVC: {filepath}")
            if result.stdout:
                logger.debug(f"DVC push stdout: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            error_msg = f"Ошибка при отправке датасета в S3 (filepath: {filepath})"
            if e.stdout:
                error_msg += f"\nStdout: {e.stdout}"
            if e.stderr:
                error_msg += f"\nStderr: {e.stderr}"
            logger.error(error_msg)
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке датасета в S3: {str(e)} (filepath: {filepath})")
            return False

    def pull_dataset(self, filepath: str) -> bool:
        """
        Загрузить датасет из удаленного хранилища.

        Args:
            filepath: Путь к файлу датасета

        Returns:
            True если успешно, False иначе
        """
        try:
            subprocess.run(
                ["dvc", "pull", "-r", self.remote, filepath],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Датасет загружен из удаленного хранилища")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Ошибка при загрузке датасета {filepath}: {str(e)}"
            )
            return False

    def list_datasets(self) -> list:
        """
        Получить список датасетов в DVC.

        Returns:
            Список путей к датасетам
        """
        try:
            result = subprocess.run(
                ["dvc", "list", "."],
                capture_output=True,
                text=True,
                check=True,
            )
            datasets = []
            for line in result.stdout.split("\n"):
                if line.strip().endswith(".dvc"):
                    datasets.append(line.strip())
            return datasets
        except subprocess.CalledProcessError as e:
            logger.error("Ошибка при получении списка датасетов")
            return []

dvc_service = DVCService()

