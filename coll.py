import os
import sys
import uuid
import shutil
import sqlite3
import mimetypes
import subprocess

from config import DATA, COLL_PATH, DB_PATH

if not COLL_PATH:
    COLL_PATH = os.path.join(os.environ["HOME"], "media")

if not DB_PATH:
    DB_PATH = os.path.join(COLL_PATH, "coll.db")

DEBUG = False
DATA_INDEX = 0

def init_db():
    if not os.path.exists(COLL_PATH): os.mkdir(COLL_PATH)

    db_con = sqlite3.connect(DB_PATH)
    db_cur = db_con.cursor()

    db_cur.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            media_type TEXT NOT NULL
        );
    """)

    db_cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            tag_name TEXT NOT NULL UNIQUE
        );
    """)

    db_cur.execute("""
        CREATE TABLE IF NOT EXISTS media_tags (
            media_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (media_id, tag_id),
            FOREIGN KEY (media_id) REFERENCES media (id),
            FOREIGN KEY (tag_id) REFERENCES tags (id)
        );
    """)

    db_con.commit()
    db_con.close()

def import_media(file_list: list[str]):
    for file in file_list:
        if file and os.path.exists(file):
            extension = os.path.splitext(file)[1]
            filename = uuid.uuid4().hex

            media_dir = mimetypes.guess_type(file)[0].split('/')

            if media_dir[1] == "gif":
                media_dir = media_dir[1]
            else:
                media_dir = media_dir[0]

            destination = os.path.join(COLL_PATH, media_dir, filename + extension)

            media_type_dir = os.path.join(COLL_PATH, media_dir)

            if not os.path.exists(media_type_dir):
                os.mkdir(media_type_dir)

            shutil.copy(file, destination)

            insert_media(destination)

            print(f"COPIED: '{file}' -> '{destination}'")
            print("")
        else: continue

def preview_media(file_path: str) -> subprocess.Popen | None:
    preview_img = input("Preview media before prompt tags? [y/n]: ")

    media_type = mimetypes.guess_type(file_path)[0].split('/')[0]

    if preview_img == "y" or preview_img == "yes":
        match media_type:
            case "image":
                return subprocess.Popen(
                    ["nsxiv", "-q", "-a", file_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            case "video":
                return subprocess.Popen(
                    ["mpv", "--really-quiet", "--loop=yes", file_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            case _: return None

    return None

def insert_media(file_path: str):
    global DEBUG
    global DATA_INDEX

    if DEBUG:
        title = DATA[DATA_INDEX][0]
        tags = DATA[DATA_INDEX][1].split()
    else:
        prev_img = preview_media(file_path)

        print("")
        print("Provide info for the media")
        title = input("Title: ")
        tags = input("Tags (separated by spaces): ").split()
        print("")

    if not title:
        proceed = input("You didn't provide a title, continue? [y/n]: ")
        if proceed == "n": return

    if not tags:
        proceed = input("You didn't provide the tags, continue? [y/n]: ")
        if proceed == "n": return

    db_con = sqlite3.connect(DB_PATH)
    db_cur = db_con.cursor()

    media_type = mimetypes.guess_type(file_path)[0].split('/')[0]

    db_cur.execute(
        "INSERT INTO media (title, file_path, media_type) VALUES (?, ?, ?)",
        (title, file_path, media_type)
    )

    media_id = db_cur.lastrowid

    for tag_name in tags:
        db_cur.execute("SELECT id FROM tags WHERE tag_name = ?", (tag_name,))
        tag_row = db_cur.fetchone()

        if tag_row:
            tag_id = tag_row[0]
        else:
            db_cur.execute("INSERT INTO tags (tag_name) VALUES (?)", (tag_name,))
            tag_id = db_cur.lastrowid

        db_cur.execute(
            "INSERT INTO media_tags (media_id, tag_id) VALUES (?, ?)", (media_id, tag_id)
        )

    if not DEBUG and prev_img is not None:
        prev_img.terminate()

    db_con.commit()

    print("SUCCESSFUL: Image was added to database")

    db_con.close()

def search_media_by_tag(tags: list[str]):
    db_con = sqlite3.connect(DB_PATH)
    db_cur = db_con.cursor()

    results: list[str] = []

    query = """
        SELECT DISTINCT media.file_path FROM media
        JOIN media_tags ON media_tags.media_id = media.id
        JOIN tags ON media_tags.tag_id = tags.id
        WHERE {}
    """.format(" OR ".join("tags.tag_name = ?" for _ in tags))

    results_path = db_cur.execute(query, tags)

    for row in results_path.fetchall():
        results.append(row[0])

    for r in results:
        print(r)

    db_con.close()

def show_media_info(id: str):
    db_con = sqlite3.connect(DB_PATH)
    db_cur = db_con.cursor()

    query = f"SELECT * FROM media WHERE id = {id}"

    results = db_cur.execute(query).fetchone()

    if results is None:
        print(f"INFO: the id '{id}' was not found")
        return

    query = f"""
        SELECT tags.tag_name FROM media
        JOIN media_tags ON media.id = media_tags.media_id
        JOIN tags ON media_tags.tag_id = tags.id
        WHERE media.id = {id}
    """

    tag_results = db_cur.execute(query).fetchall()

    id, title, file_path, media_type = results
    tags = " ".join([row[0] for row in tag_results])

    print("ID:   ",id)
    print("TYPE: ",media_type)
    print("TITLE:",title)
    print("TAGS: ",tags)
    print("PATH: ",file_path)

    db_con.close()

def modify_media(id: str):
    db_con = sqlite3.connect(DB_PATH)
    db_cur = db_con.cursor()

    old_title = db_cur.execute("SELECT title FROM media WHERE id = ?", (id,)).fetchone()

    if old_title is None:
        print(f"INFO: the id '{id}' was not found")
        return

    print("Provide new info for the media:")
    print("Old Title:", old_title[0])
    title = input("New Title: ")

    query = f"UPDATE media SET title = '{title}' WHERE id = {id}"

    db_cur.execute(query)
    db_con.commit()
    print("INFO: the title was modified")

    db_con.close()

def delete_media(id: str):
    db_con = sqlite3.connect(DB_PATH)
    db_cur = db_con.cursor()

    result = db_cur.execute("SELECT 1 FROM media WHERE id = ?", (id,)).fetchone()

    if result is None:
        print(f"INFO: the id '{id}' was not found")
        return

    query = f"DELETE FROM media WHERE id = {id}"

    db_cur.execute(query)
    db_con.commit()
    print("INFO: the media was deleted")

    db_con.close()

def clean():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("DELETED:", DB_PATH)

        if os.path.exists(COLL_PATH):
            # shutil.rmtree(COLL_PATH)
            # print("DELETED:", COLL_PATH)

            for root, dirs, files in os.walk(COLL_PATH, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                    print(f"DELETED: {root}/{file}")
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
                    print(f"DELETED: {root}/{dir}")

            os.rmdir(COLL_PATH)
            print("DELETED:", COLL_PATH)

def parse_subcommand(args: list[str]):
    match args[0]:
        case "import":
            import_options = args[1:]
            if not import_options: print_usage()
            import_media(import_options)

        case "search":
            search_options = args[1:]
            if not search_options: print_usage()
            search_media_by_tag(search_options)

        case "info":
            info_options = args[1:]
            if not info_options: print_usage()
            show_media_info(info_options[0])

        # TODO: Reformulate modify
        # Because tables changed
        case "modify":
            modify_options = args[1:]
            if not modify_options: print_usage()
            modify_media(modify_options[0])

        # TODO: Reformulate delete
        # Because tables changed
        case "delete":
            delete_options = args[1:]
            if not delete_options: print_usage()
            delete_media(delete_options[0])

        case "test":
            global DATA_INDEX
            global DEBUG
            DEBUG = True

            for data in DATA:
                import_media([data[2]])
                DATA_INDEX += 1

        case "clean":
            clean()

        case _:
            print_usage()

    sys.exit()

def print_usage():
    print("Usage: coll.py [OPTIONS] subcommand [args...]")
    print("")
    print("Subcommands:")
    print("    import  Import new media to the library")
    print("    search  Search for media with specified tag in the library")
    print("    info    Show every info about an media")
    print("    modify  Modify the title of the media")
    print("    delete  Delete a media")
    print("    clean   Delete everything, including media and database")
    print("")
    print("Options:")
    print("    -h, --help  Print this help")
    sys.exit()

def main():
    init_db()

    args = sys.argv[1:]

    if not args: print_usage()

    for arg in args:
        match arg:
            case "-h" | "--help": print_usage()
            case _: parse_subcommand(args)

if __name__ == "__main__":
    main()

