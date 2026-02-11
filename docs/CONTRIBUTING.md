# Contributing to CANChat

🚀 **Welcome, Contributors!** 🚀

Your interest in contributing to CANChat is greatly appreciated. This document is here to guide you through the process, ensuring your contributions enhance the project effectively. Let's make CANChat even better, together!

## 📌 Key Points

### 🦙 Ollama vs. CANChat

It's crucial to distinguish between Ollama and CANChat:

- **CANChat** focuses on providing an intuitive and responsive web interface for chat interactions.
- **Ollama** is the underlying technology that powers these interactions.

If your issue or contribution pertains directly to the core Ollama technology, please direct it to the appropriate [Ollama project repository](https://ollama.com/). CANChat's repository is dedicated to the web interface aspect only.

### 🚨 Reporting Issues

Noticed something off? Have an idea? Check our [Issues tab](https://github.com/ssc-dsai/canchat-v2/issues) to see if it's already been reported or suggested. If not, feel free to open a new issue. When reporting an issue, please follow our issue templates. These templates are designed to ensure that all necessary details are provided from the start, enabling us to address your concerns more efficiently.

> [!IMPORTANT]
>
> - **Template Compliance:** Please be aware that failure to follow the provided issue template, or not providing the requested information at all, will likely result in your issue being closed without further consideration. This approach is critical for maintaining the manageability and integrity of issue tracking.
> - **Detail is Key:** To ensure your issue is understood and can be effectively addressed, it's imperative to include comprehensive details. Descriptions should be clear, including steps to reproduce, expected outcomes, and actual results. Lack of sufficient detail may hinder our ability to resolve your issue.

### 🧭 Scope of Support

We've noticed an uptick in issues not directly related to CANChat but rather to the environment it's run in, especially Docker setups. While we strive to support Docker deployment, understanding Docker fundamentals is crucial for a smooth experience.

- **Docker Deployment Support**: CANChat supports Docker deployment. Familiarity with Docker is assumed. For Docker basics, please refer to the [official Docker documentation](https://docs.docker.com/get-started/overview/).

- **Advanced Configurations**: Setting up reverse proxies for HTTPS and managing Docker deployments requires foundational knowledge. There are numerous online resources available to learn these skills. Ensuring you have this knowledge will greatly enhance your experience with CANChat and similar projects.

## 💡 Contributing

Looking to contribute? Great! Here's how you can help:

### 🛠 Pull Requests

We welcome pull requests, including from public contributors.

Before submitting one, please:

1. Follow the PR template in `.github/pull_request_template.md`.
2. Use a conventional PR title prefix: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `style`, or `revert`.
3. Target the `dev` branch unless a maintainer explicitly asks otherwise.
4. Include tests you ran and their outcomes in the PR body.
5. Complete the PR body changelog section (`Added`, `Changed`, `Fixed`, `Removed`, `Security`, `Breaking`), using `N/A` where applicable.
6. Keep PRs moving. If a PR remains inactive for too long, maintainers may close it to keep delivery flow healthy.

### ✅ PR Template Reminder Bot

This repository runs a comment-only PR template validator.
Reference: <https://docs.github.com/en/actions/reference/workflows-and-actions>

- If required title/body fields are missing, the bot adds the label `needs-pr-template-fix` and leaves a checklist comment.
- When everything is complete, the bot updates its comment and removes the label.
- The check does not block merges directly; it is a governance signal for contributors and reviewers.

### 👀 Reviewer Governance

Reviewers should use the following rules:

1. Do not approve PRs that have the `needs-pr-template-fix` label.
2. Request template completion when required sections are missing or still contain placeholders.
3. Do not require Jira ticket IDs for external/public contributions.

### 📚 Documentation & Tutorials

Help us make CANChat more accessible by improving documentation, writing tutorials, or creating guides on setting up and optimizing the web UI.

### 🌐 Translations and Internationalization

Help us make CANChat available to a wider audience. In this section, we'll guide you through the process of adding new translations to the project.

We use JSON files to store translations. You can find the existing translation files in the `src/lib/i18n/locales` directory. Each directory corresponds to a specific language, for example, `en-US` for English (US), `fr-FR` for French (France) and so on. You can refer to [ISO 639 Language Codes](http://www.lingoes.net/en/translator/langcode.htm) to find the appropriate code for a specific language.

To add a new language:

- Create a new directory in the `src/lib/i18n/locales` path with the appropriate language code as its name. For instance, if you're adding translations for Spanish (Spain), create a new directory named `es-ES`.
- Copy the American English translation file(s) (from `en-US` directory in `src/lib/i18n/locale`) to this new directory and update the string values in JSON format according to your language. Make sure to preserve the structure of the JSON object.
- Add the language code and its respective title to languages file at `src/lib/i18n/locales/languages.json`.

### 🤔 Questions & Feedback

Got questions or feedback? Join our [Discord community](https://discord.gg/5rJgQTnV4s) or open an issue. We're here to help!

## 🙏 Thank You

Your contributions, big or small, make a significant impact on CANChat. We're excited to see what you bring to the project!

Together, let's create an even more powerful tool for the community. 🌟
