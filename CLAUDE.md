# Profile README (github.com/frimpongopoku)

This repo is the GitHub profile README. `README.md` and everything in `assets/` are generated. Never edit them by hand.

## Where things live

- `profile.yml`: all content. Hero text, agent sidebar, badges, toolkit, loop, projects, stack, footer. Most change requests are an edit here.
- `README.template.md`: section order and layout. `{{placeholders}}` are filled by the build.
- `scripts/build.py`: draws the SVGs (hero, cards, stats, kente) and writes README.md. Visual changes (colours, sizes, card layout) go here.
- `scripts/preview.py`: renders README.md through GitHub's markdown API into `preview.html` with local images.
- `.github/workflows/build.yml`: rebuilds on push and every Monday, so the repo and language counts stay current.

## Making a change

1. Edit `profile.yml` (or the template or build script).
2. `make build`. It fails loudly on duplicate project ids or unknown placeholders.
3. `make preview` and look at it. To check it yourself without a browser, screenshot `preview.html` with headless Chrome using `--timeout=5000` (not `--virtual-time-budget`, which hangs on the looping SVG animations).
4. Show the user, then `make ship m="what changed"` once they approve. That's what makes it go live.

## Common requests

- **Feature or hide a project**: flip `featured:` on its entry. Order in the file is order on the page.
- **Add a project**: new entry under `projects:` with a unique `id`, `lane` (studio | pro | vault), `status` (live | wip | work; not needed for vault), `blurb`, `tags`, optional `url` and `shipped_in`.
- **Back up the speed claim**: fill `shipped_in` on a card (e.g. "9 days"). Use only real numbers from the user.

## Rules

- No dates, timestamps, commit activity, streaks or heatmaps anywhere on the README. The user doesn't want side-project work times on show next to the day job.
- Keep the two lanes separate: Biibisoft products in `studio`, MassEnergize work in `pro`.
- `me-ai` (Newsletter AI pipeline) stays `featured: false` until the user confirms MassEnergize is fine with showing it.
- Don't invent claims or metrics. Ask the user if a number is needed.
- Don't add Co-Authored-By lines to commits.
- Project blurbs: short, plain, one or two sentences, max three lines on the card (the build cuts longer ones with an ellipsis).
