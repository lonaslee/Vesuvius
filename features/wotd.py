import wikipedia
import random
import vsvs_config


async def randword():
    # no async because slow
    with open(vsvs_config.files_dict['words_alpha'], 'r') as f:
        allwords = f.readlines()
        for k, w in enumerate(allwords):
            allwords[k] = w.removesuffix('\n')
    word = random.choice(allwords)
    return word


async def defineword():
    while word := await randword():
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


async def oneworder():
    wd = await defineword()
    while len(wd[0].split(' ')) > 1 and '()' not in wd[0]:
        wd = await defineword()
    if len(wd[1]) > 4090:
        return wd[0], wd[1][:4099] + '...', wd[2], wd[3]
    return wd
