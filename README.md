# Coll

Coll is a media organizer system for the people who collect digital stuff.

It's main purpose is to generate a tag system for the files inside your library, so you can query for them and maybe use it inside a script.

This not a media tagger for movies, comics or music. It's targeted for personal media libraries, like your travel pictures or your meme collection.

## Example

```
$ python coll.py import ./funny-meme.jpg

Preview media before prompt tags? [y/n]: n

Provide info for the media
Title: Cursed cat looking at you
Tags (separated by spaces): cat confusing cursed
```

## How to run

For now, `git clone` this repo and:

```shell
python coll.py --help
```

You can setup a different library path and database path using a config.py.

`config.py`:

```python
import os

COLL_PATH = os.path.join(os.environ["HOME"], "media")
DB_PATH = os.path.join(COLL_PATH, "coll.db")
```

## References

Things that inspired me or helped me to make this project.

- [beets](https://github.com/beetbox/beets)
