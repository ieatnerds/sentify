# coding=utf-8
import os
import sys
import argparse

from time import sleep
import colour
import spectra # Create color gradient in scales()
#from led_controller import LEDController
from current_spotify_playback import CurrentSpotifyPlayback, NoArtworkException
from spotify_background_color import SpotifyBackgroundColor
from PIL import ImageColor
import dbutil # custome sqlite3 utilities
from datetime import datetime # For timing operations
from secret import * # Credentials for API access
import sengled


def rgb2hsv(r, g, b):
    r,g,b = int(r), int(g), int(b)
    r, g, b = r/255.0, g/255.0, b/255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx-mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g-b)/df) + 360) % 360
    elif mx == g:
        h = (60 * ((b-r)/df) + 120) % 360
    elif mx == b:
        h = (60 * ((r-g)/df) + 240) % 360
    if mx == 0:
        s = 0
    else:
        s = df/mx
    v = mx

    return h, s, v


# def scales(starthex, endhex):
#     """Takes to hex colors and creates a list of colors inbetween to create a gradient"""
#     my_scale = spectra.range([starthex, endhex], 100)
#     colorlist = []
#     for i, item in enumerate(my_scale):
#         colorlist.append(item.hexcode)
#     return colorlist


def set_lights(lights, color, brightness):
    """ This function will set the color of sengled rgb lights
        lights: List of light objectsd returned by the sengled API
        color: List of r, g, and b color values
        brightness: integer 0-100 for brightness of bulb """
    for light in lights:
        light.set_color(color).set_brightness(brightness)


def tohex(r, g, b):
    """ Returns a hex color representation in the form of
    #xxxxxx """
    r, g, b = int(r), int(g), int(b)
    hexrep = '#%02x%02x%02x' % (r, g, b)
    return hexrep


def main(k, color_tol, size):
    """Sets Sengled RGB Lights to sporify album color

    Args:
        k (int): Number of clusters to form.
        color_tol (float): Tolerance for a colorful color.
            Colorfulness is defined as described by Hasler and
            Süsstrunk (2003) in https://infoscience.epfl.ch/record/
            33994/files/HaslerS03.pdf.
        size: (int/float/tuple): Process image or not.
            int - Percentage of current size.
            float - Fraction of current size.
            tuple - Size of the output image.

    """
    ### Start Sengled API ###
    api = sengled.api(SENGLED_USERNAME, SENGLED_PASSWORD, debug=False)
    lights = api.filter_color_temperature_lamps()

    ### Start DB Connections ###
    sql_create_songs_table = """ CREATE TABLE IF NOT EXISTS songs (
                                    id text PRIMARY KEY,
                                    rgbcolor text,
                                    hexcolor text,
                                    brightness text,
                                    sname text,
                                    sartists text
                                    );"""

    database = "./sentify.db"
    conn = dbutil.create_connection(database)
    if conn is not None:
        dbutil.create_table(conn, sql_create_songs_table)
    else:
        print("Error! Cannot create the DB connection")
        exit()

    #GPIO_PINS = config['GPIO PINS']
    #red_pin = int(GPIO_PINS['red_pin'])
    #green_pin = int(GPIO_PINS['green_pin'])
    #blue_pin = int(GPIO_PINS['blue_pin'])
    #name = config['CHROMECAST']['name']
    #led = LEDController(red_pin, green_pin, blue_pin)

    ### Start Spotify API ###
    spotify = CurrentSpotifyPlayback(CLIENT_ID, CLIENT_SECRET,
                                     REDIRECT_URI, REFRESH_TOKEN)
    old_song_id = ''
    try:
        r, g, b = 0, 0, 0
        brightness = 0
        while True:
            spotify.update_current_playback()
            if spotify.new_song(old_song_id):
                ##GET SONG INFO##
                sname = spotify.get_current_song_name() #song name
                sartists = spotify.get_current_song_artists() # main artist for song
                old_song_id = spotify.get_current_song_id()
                if not dbutil.song_exists(conn, old_song_id): # If song doesnt exist, create it
                    try: # only if it has album art tho
                        start_time = datetime.now()
                        artwork = spotify.get_artwork()
                        background_color = SpotifyBackgroundColor(img=artwork, image_processing_size=size)
                        r, g, b = background_color.best_color(k=8, color_tol=10)
                        r, g, b = str(int(round(r))), str(int(round(g))), str(int(round(b)))
        
                        rgbrep = str(r) + " " + str(g) + " " + str(b)
                        hexrep = tohex(r, g, b)
                        brightness = int(((rgb2hsv(r, g, b)[2]) * 100) // 1)

                        songinfo = [old_song_id, rgbrep, hexrep, brightness, sname, sartists]
                        dbutil.create_song(conn, songinfo)
                        conn.commit()
                        time_elapsed = datetime.now() - start_time 
                        print('Entry Created in: (hh:mm:ss.ms) {}'.format(time_elapsed))

                    except NoArtworkException:
                        r, g, b = 255, 255, 255
                        brightness = 100
                #led.set_color(r, g, b)
                start_time = datetime.now()
                rawdata = dbutil.select_song_info(conn, old_song_id)
                time_elapsed = datetime.now() - start_time
                print('Entry Found in: (hh:mm:ss.ms) {}'.format(time_elapsed))

                color = rawdata[1].split()
                r,g,b = color
                r,g,b = int(r), int(g), int(b)
                hexrep = rawdata[2]
                brightness = int(rawdata[3])
                set_lights(lights, color, brightness)
                song = sname+" - "+sartists # gives "song name - song artist" 
                print(song, " : ", r, "r ", g, "g ", b, "b ", hexrep, " brightness: ", brightness, "%\n", sep = '') # prints logging of song/artist and the color for the song
            sleep(3)
            
    except KeyboardInterrupt:
        conn.close()
        exit() #led.set_color(0, 0, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Runs the Spotify '\
                                    'background color script')
    parser.add_argument('-k', '--cluster', metavar='NUMBER', type=int,
                        default=8, help='number of clusters used in '\
                        'the k-means clustering')
    parser.add_argument('-t', '--tol', metavar='TOLERANCE', type=float,
                        default=0, help='tolerance for a colorful color')
    parser.add_argument('-s', '--size', metavar='SIZE', type=int, nargs='+',
                        default=(100, 100), help='artwork width and height to use')

    args = parser.parse_args()
    main(args.cluster, args.tol, tuple(args.size))
