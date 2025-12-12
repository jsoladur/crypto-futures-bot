import importlib
from os import listdir, path


def load_modules_by_folder(root_folder: str, root_package: str, folder_name: str) -> None:
    if path.exists(root_folder) and path.isdir(root_folder):
        current_folder = path.join(root_folder, folder_name)
        if path.exists(current_folder) and path.isdir(current_folder):
            for filename in listdir(current_folder):
                if path.isdir(path.join(current_folder, filename)):
                    load_modules_by_folder(
                        root_folder=current_folder, root_package=f"{root_package}.{folder_name}", folder_name=filename
                    )
                elif filename.endswith(".py") and filename != "__init__.py":
                    module_name = f"{root_package}.{folder_name}.{filename[:-3]}"
                    importlib.import_module(module_name)
