import wikipedia
import random
from typing import TYPE_CHECKING
from random import choice

# if TYPE_CHECKING:
from pathlib import Path


async def _randword(path: str | Path):
    # no async because slow
    with open(path, 'r') as f:
        allwords = f.readlines()
        for k, w in enumerate(allwords):
            allwords[k] = w.removesuffix('\n')
    word = random.choice(allwords)
    return word


async def _defineword(path: str | Path) -> tuple[str, str, str, str]:
    while word := await _randword(path):
        try:
            page = wikipedia.page(word)
            break
        except wikipedia.PageError:
            continue
        except wikipedia.DisambiguationError as disamb:
            longest = (int(), None)
            for n in range(5):
                try:
                    pg: wikipedia.WikipediaPage = wikipedia.page(disamb.options[n])
                except (wikipedia.DisambiguationError, wikipedia.PageError):
                    continue
                if (l := len(pg.content)) > longest[0]:
                    longest = (l, pg)
            page = longest[1]
            break
    try:
        return (
            page.title,
            page.summary.removesuffix('\n'),
            page.url,
            choice(page.images),
        )
    except (KeyError, IndexError):
        return page.title, page.summary.removesuffix('\n'), page.url, None


async def oneworder(path: str | Path):
    wd = await _defineword(path)
    while len(wd[0].split(' ')) > 1 and '()' not in wd[0]:
        wd = await _defineword(path)
    if len(wd[1]) > 4090:
        return wd[0], wd[1][:4000] + '...', wd[2], wd[3]
    return wd


async def get_wiki_page(title: str) -> tuple[str, str, str, str]:
    try:
        page: wikipedia.WikipediaPage = wikipedia.page(title)
        summary: str = page.summary
        if len(page.summary) > 4090:
            summary = page.summary[:4000]
        return page.title, summary.removesuffix('\n'), page.url, choice(page.images)
    except Exception:
        raise ValueError
