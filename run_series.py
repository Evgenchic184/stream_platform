import subprocess
import os
import time

def show_season(last_series: str):
    dirname = os.path.dirname(last_series)
    basename = os.path.basename(last_series)
    list_dir = sorted(os.listdir(dirname))
    current_index = (list_dir.index(basename))
    for i in range(current_index, len(list_dir)):
        path_to_series = os.path.join(dirname, list_dir[i])
        with open("history", "w") as f:
            print(path_to_series, file=f)
        print(path_to_series)
        #time.sleep(0.1)
        subprocess.run(["bash", "show.sh", path_to_series, "&>", "/dev/null"])


def change_season(last_series: str) -> str:
    dirname = os.path.dirname(last_series)
    season_name = os.path.basename(dirname)
    
    season_dir = os.path.dirname(dirname)
    list_dir = sorted(os.listdir(season_dir))
    current_index_season = list_dir.index(season_name)
    next_index_season = (current_index_season + 1) % len(list_dir)
    
    new_season_path = os.path.join(season_dir, list_dir[next_index_season])

    first_series_name = sorted(os.listdir(new_season_path))[0]
    print(new_season_path, os.listdir(new_season_path))
    print(f"new season starts with: {first_series_name}")
    return os.path.join(new_season_path, first_series_name)
    

   
if __name__ == "__main__":
    
    with open("history", "r") as f:
        last_series = f.readline().strip()
    print(f"history: {last_series}")

    while True:
        show_season(last_series)
        last_series = change_season(last_series)


