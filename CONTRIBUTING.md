# Contributing

## 🌍 This Project is Community-Owned

This project follows an **open contribution model**. There is no gatekeeping — anyone can contribute, anyone can fork, and anyone can improve the code.

## How to Contribute

### Option 1: Fork and Improve (Recommended)

The easiest way to contribute is to **fork this repo** and make your changes:

1. Click the **Fork** button at the top right of this page
2. Make your changes in your fork
3. Submit a **Pull Request** back to this repo

Pull requests are welcome for:
- Bug fixes
- New commands
- Performance improvements
- Documentation updates
- Additional anti-detection features
- New research protocols

### Option 2: Fork and Go Your Own Way

If you want to take the project in a completely different direction, **feel free to fork it and make it your own**. The MIT license allows you to do anything with this code. No permission needed.

### Option 3: Open an Issue

Found a bug or have a feature idea? [Open an issue](https://github.com/Longjumping-Mango/discord-research-antigravity/issues) and describe it.

## Guidelines

- **No personal tokens** in code — tokens should come from environment variables or CLI flags
- **Read-only operations only** — this tool must never write to Discord (no sending messages, no reactions, no modifications)
- **Rate limiting** — all API calls must respect Discord's rate limits
- **Anti-detection** — maintain browser-like headers to protect users' accounts
- **Test your changes** — verify all 10 commands still work before submitting a PR

## Code Style

- Python 3.10+
- Use type hints
- Async/await for all API calls
- Docstrings for all public functions

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
