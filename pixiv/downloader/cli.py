import argparse
import sys
from . import PixivDownloader


def main():
    parser = argparse.ArgumentParser(usage="""Pixiv Downloader

To start CLI UI:
>>> python app.py

To start downloads directly:
>>> python app.py "XXXXXXXX" "https://www.pixiv.net/en/artworks/XXXXXXXX"

If the user is not logged in yet the CLU UI starts and asks for login credentials.
This can be disabled with useing --username and --password to log in. If only one
of those is given then the Login CLI UI will be started asking for the missing value. So
eg. in this case the UI will start and ask for a password:
>>> pytohn app.py "XXXXXXXX" -u my_user

If you want to disable the CLI UI completly and just exit if no username and
passords are given then use -q.
>>> python app.py "XXXXXXXX" -q
""")

    parser.add_argument('-u', '--username', help='Pixiv username')
    parser.add_argument('-p', '--password', help='Pixiv password')
    parser.add_argument('-q', '--quiet', help='Disable login prompt when direct download is used',
                        action='store_true')
    parser.add_argument('posts', nargs='*', help='URLs or post IDs of pixiv posts to download')

    args = parser.parse_args()
    app = PixivDownloader()
    if args.posts:
        if not app.logged_in:
            if args.quiet and (not args.username or args.password):
                sys.exit(1)
            print('Login to Pixiv')
            app.login_menu(args.username, args.password, try_again=not (args.password and args.username))

            if not app.logged_in:
                sys.exit(1)

        for post in args.posts:
            app.download_by_url_or_id(post)
    else:
        app.start()
