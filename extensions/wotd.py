from __future__ import annotations

from random import choice
from typing import TYPE_CHECKING

import wikipedia

if TYPE_CHECKING:
    from pathlib import Path


__all__ = ('oneworder', 'get_wiki_page')


async def _randword(path: str | Path) -> str:
    # no async because slow
    with open(path, 'r') as f:
        return choice(f.readlines()).removesuffix('\n')


async def _defineword(path: str | Path) -> tuple[str, str, str, str]:
    page = None
    while word := await _randword(path):
        try:
            page = wikipedia.page(word)
            break
        except wikipedia.PageError:
            continue
        except wikipedia.DisambiguationError as disamb:
            longest = (0, None)
            for n in range(5):
                try:
                    pg: wikipedia.WikipediaPage = wikipedia.page(disamb.options[n])
                    if not await _category_filter(pg.categories):
                        continue
                except (wikipedia.DisambiguationError, wikipedia.PageError):
                    continue
                if (l := len(pg.content)) > longest[0]:
                    longest = (l, pg)
            page = longest[1]
            break
    assert isinstance(page, wikipedia.WikipediaPage)
    try:
        return (
            page.title,
            page.summary.removesuffix('\n'),
            page.url,
            choice(page.images),
        )  # type: ignore
    except (KeyError, IndexError):
        return page.title, page.summary.removesuffix('\n'), page.url, None


async def _category_filter(__categories: list[str]) -> bool:
    blacklist = ('film', 'character', 'fiction', 'movie', 'game')
    for category in __categories:
        for word in blacklist:
            if word in category.lower():
                return False
    return True


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
        return '', '', '', ''
