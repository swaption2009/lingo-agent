import sys

def generate_phonetic(text: str) -> str:
    # Simplified mock phonetic guide rules for beginner Spanish learners
    words = text.lower().split()
    phonetics = []
    for word in words:
        p = word
        # ll -> y (e.g., ella -> eya)
        p = p.replace("ll", "y")
        # z -> s (e.g., cabeza -> cabesa)
        p = p.replace("z", "s")
        # v -> b (e.g., vivir -> bibir)
        p = p.replace("v", "b")
        # j -> h (e.g., jamon -> hamon)
        p = p.replace("j", "h")
        # ge -> he, gi -> hi (e.g., gente -> hente)
        p = p.replace("ge", "he").replace("gi", "hi")
        # h at start of word is silent
        if p.startswith("h"):
            p = p[1:]
        
        # strip punctuation
        p = "".join(c for c in p if c.isalnum() or c in "áéíóúüñ")
        phonetics.append(p)
    return " ".join(phonetics)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 phonetic_generator.py <text>")
        sys.exit(1)
        
    text = " ".join(sys.argv[1:])
    print(generate_phonetic(text))
