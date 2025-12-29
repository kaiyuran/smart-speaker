import ollama

MODEL = "speakerAssistantv5"

def main():
    print("Ollama streaming test (Ctrl+C to quit)")
    print("-" * 40)

    history = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            history.append({
                "role": "user",
                "content": user_input
            })

            print("Assistant:", end=" ", flush=True)

            stream = ollama.chat(
                model=MODEL,
                messages=history,
                stream=True
            )

            full_reply = ""

            for chunk in stream:
                # print(chunk)

                try:
                    token = chunk.message.content
                    print(token, end="")#, flush=True)
                    full_reply += token
                except:
                    pass
            # print()
            history.append({
                "role": "assistant",
                "content": full_reply
            })

        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()
