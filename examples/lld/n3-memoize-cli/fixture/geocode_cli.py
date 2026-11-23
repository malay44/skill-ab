import sys
import time


def geocode(city):
    """Slow pure lookup. Same city always gives the same answer."""
    time.sleep(0.5)  # stands for a slow local computation
    return (hash(city) % 180 - 90, hash(city[::-1]) % 360 - 180)


def main(path):
    # the input file has one city per line; many cities repeat
    for line in open(path):
        city = line.strip()
        if city:
            print(city, geocode(city))


if __name__ == "__main__":
    main(sys.argv[1])
