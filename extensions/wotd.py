import wikipedia
import random


async def randword(path):
    # no async because slow
    with open(path, 'r') as f:
        allwords = f.readlines()
        for k, w in enumerate(allwords):
            allwords[k] = w.removesuffix('\n')
    word = random.choice(allwords)
    return word


async def defineword(path):
    while word := await randword(path):
        page = None
        try:
            page = wikipedia.page(word)
            break
        except wikipedia.PageError:
            continue
        except wikipedia.DisambiguationError as disamb:
            longest = (int(), None)
            for n in range(5):
                try:
                    pg = wikipedia.page(disamb.options[n])
                except (wikipedia.DisambiguationError, wikipedia.PageError):
                    continue
                if (l := len(pg.content)) > longest[0]:
                    longest = (l, pg)
            page = longest[1]
            break
    try:
        return page.title, page.summary.removesuffix('\n'), page.url, page.images[0]
    except (KeyError, IndexError):
        return page.title, page.summary.removesuffix('\n'), page.url, None


async def oneworder(path):
    wd = await defineword(path)
    while len(wd[0].split(' ')) > 1 and '()' not in wd[0]:
        wd = await defineword(path)
    if len(wd[1]) > 4090:
        return wd[0], wd[1][:4000] + '...', wd[2], wd[3]
    return wd
