import os
from glob import glob

# FILES_TO_KEEP =  {"initial.wav", "final.wav"}
FILES_TO_KEEP = set()

def delete_all_wav(files_to_keep=FILES_TO_KEEP):
    current_directory = os.getcwd()
    [os.remove(file) and print(f"Deleted: {file}") for file in glob(os.path.join(current_directory, "*.wav")) if os.path.basename(file) not in files_to_keep]


