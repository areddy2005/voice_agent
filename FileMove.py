import os
import glob
import shutil
import zipfile

def organize(
    downloads_dir: str = "~/Downloads",
    dest_dir: str = "~/Documents/SeleniumTest"
):
    # normalize paths
    downloads_dir = os.path.expanduser(downloads_dir)
    dest_dir      = os.path.expanduser(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)

    pattern = os.path.join(downloads_dir, "*")
    candidates = glob.glob(pattern)
    if not candidates:
        raise FileNotFoundError(f"No files found in {downloads_dir!r}")
    
    # pick the most recently created/modified
    latest_file = max(candidates, key=os.path.getctime)

    # branch on extension
    if latest_file.lower().endswith(".zip"):
        extract_folder = organize_latest_zip(downloads_dir, dest_dir)
        return extract_folder
    else:
        moved_path = shutil.move(latest_file, dest_dir)
        print(f"📄 Moved file to {moved_path}")
        return moved_path

def organize_latest_zip(
    downloads_dir: str = "~/Downloads",
    dest_dir: str = "~/Documents/SeleniumTest"
) -> str:
    """
    Finds the newest .zip in `downloads_dir`, moves it into `dest_dir`,
    extracts it into a same-named subfolder, then deletes the zip.
    Returns the path to the extraction folder.
    """
    # normalize paths
    downloads_dir = os.path.expanduser(downloads_dir)
    dest_dir      = os.path.expanduser(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)

    # 1) locate newest zip
    zips = glob.glob(os.path.join(downloads_dir, "*.zip"))
    if not zips:
        raise FileNotFoundError(f"No .zip files found in {downloads_dir}")
    latest_zip = max(zips, key=os.path.getctime)

    # 2) move it
    moved_zip = shutil.move(latest_zip, dest_dir)

    # 3) make extraction subfolder
    base_name      = os.path.splitext(os.path.basename(moved_zip))[0]
    extract_folder = os.path.join(dest_dir, base_name)
    os.makedirs(extract_folder, exist_ok=True)

    # 4) extract
    with zipfile.ZipFile(moved_zip, 'r') as zf:
        zf.extractall(extract_folder)

    # 5) delete original zip
    os.remove(moved_zip)

    return extract_folder
