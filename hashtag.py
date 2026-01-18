# Здесь программа будет выискивать нужные слова и давать соответствующие хэштеги

hashtags = ["#генш", "#хср", "#другое"]
hashtags_dict = [
    ["генш", "натлан", "нод-край", "архонт", "созвезди"],
    ["хср", "эйдолон", "амфореус", "двумерния", "пенакония", "экспи"],
    ["хи3", "ззз"]
] # 2 - другое

def find_words(take):
    word = ""
    hstg = ""
    for i in range(0, 3):
        for letter in take:
            if letter == " " or letter == "." or letter == ",":
                for root in hashtags_dict[i]:
                    if word.lower().startswith(root):
                        hstg.append(hashtags[i])
                word = ""
            elif letter != " " or letter != "." or letter != ",":
                word += letter        
        if word.lower() in hashtags_dict and not(hashtags[i] in hstg):
            hstg += hashtags[i]
    if len(hstg) == 0:
        hstg += hashtags[2]
    return hstg