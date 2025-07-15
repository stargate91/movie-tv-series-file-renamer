from guessit import guessit

filename = "Dzsungelből Dzsungelbe 1080p.mkv"
result = guessit(filename)

for key, value in result.items():
    print(f"{key}: {value}")
