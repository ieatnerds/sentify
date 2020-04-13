# testing creating a simple db for colors, so in theory, we can reuse color we already know for songs
# instead of having to recalculate the color each and every time. especially on rpi, this should improve power and performance
# IF I ever create a new cluster identifier algo, I can recreate the db.

## plan of execution
# create db if none exists
# db with 1 table
# key would be song id - string identifier from spotify
# data would have rgb color along with hex color

# main.py would get currently playing song.
# search db for song id, if not found, calculate color, create entry and insert data
# if song is found simply pass data to rest of main.py instead of recalculating color.
import sqlite3
from sqlite3 import Error


def create_connection(db_file):
    "create db connection to sqlite db"
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn

    except Error as e:
        print(e)

    return conn


def create_table(conn, create_table_sql):
    "takes db conn, and create table statement in sql format"
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def create_song(conn, songinfo):
    """takes db conn, and song info list"""
    sql = f'''INSERT  OR IGNORE INTO songs (id, rgbcolor, hexcolor, brightness, sname, sartists) 
    VALUES ("{songinfo[0]}","{songinfo[1]}","{songinfo[2]}","{songinfo[3]}","{songinfo[4]}","{songinfo[5]}")'''
    current = conn.cursor()
    current.execute(sql)

    return current.lastrowid

def select_all_songs(conn):
    """ gets all songs from table"""
    current = conn.cursor()
    current.execute("SELECT * FROM songs")
    rows = current.fetchall()
    print(rows)
    for row in rows:
        print(row)

def select_song_info(conn, song):
    """take db connection - search song id - return tuple with rgb and hex colors"""
    current = conn.cursor()
    data = current.execute(f'SELECT * FROM songs WHERE ID="{song}"')
    for item in data:
        return item

def song_exists(conn, song):
    """Return true or false for if a song already exists in the db"""
    current = conn.cursor()
    data = current.execute(f'SELECT * FROM songs WHERE id="{song}"')
    data = current.fetchone()
    if data is None:
        return False

    return True
