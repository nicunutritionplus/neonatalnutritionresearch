# Neonatal Nutrition Research

Static website for [neonatalnutritionresearch.com](https://neonatalnutritionresearch.com), rebuilt from the original GoDaddy Website Builder site so it can live in a GitHub repository and be served by GitHub Pages.

- Plain HTML, CSS and a little vanilla JavaScript. No framework, no runtime dependencies.
- Fonts are self-hosted and the site sets no cookies and loads nothing from third parties, so no cookie banner is needed.
- The finished HTML is committed to the repo, so GitHub Pages can serve it directly. A small Python script regenerates that HTML from the files in `content/`.

## Quick start

Requires Python 3.8+ (standard library only).

```bash
python3 tools/build.py              # regenerate the site from content/
python3 -m http.server 8000         # preview at http://localhost:8000
```

`build.py` also checks that every internal link, image and anchor in the output resolves, and exits with an error if one does not.

> Open the site through a web server as above rather than double-clicking `index.html`; pages link to folders (`about-us/`), which browsers only resolve on a server.

## Where things live

```
content/
  site.json           site name, URL, navigation, contact details, form endpoint
  pages/*.html        the page text (About, Studies, Resources, Milk, ...)
  posts/*.html        one file per news post
  publications.json   the publications list, grouped by type
  studies.json        active and recently completed studies
  team.json           the team section on the About page
assets/               css, js, fonts, images
tools/build.py        the site generator
```

Everything outside `content/` and `assets/` (the `index.html` files, `f/`, `feed.xml`, `sitemap.xml`, ...) is **generated**: change the sources, run `python3 tools/build.py`, and commit the result. Do not edit generated files by hand.

## Common edits

**Add a news post.** Copy any file in `content/posts/`, rename it, and edit the front matter and body:

```html
---
title: My new post
slug: my-new-post
date: 2026-10-01
image: assets/img/posts/my-image.jpg
imageAlt: Short description of the image
---
<p>First paragraph. It becomes the summary on the home page.</p>
<h2>A heading</h2>
<p>More text with <a href="https://example.org">a link</a>.</p>
<figure><img src="{{root}}assets/img/posts/chart.png" alt="What the chart shows"></figure>
```

Put images in `assets/img/posts/`. Keep `{{root}}` in front of local paths; the build replaces it with the right relative path. The `slug` becomes the URL (`/f/my-new-post/`). Optionally add `excerpt: ...` to the front matter to override the automatic summary.

**Add a publication.** Add an entry to a group in `content/publications.json` (`authors`, `title`, `url`, `source`, `freeArticle`, `tags`). New topic tags automatically appear as filter buttons.

**Update studies or the team.** Edit `content/studies.json` or `content/team.json`. Team photos go in `assets/img/team/`. A person with `"photo": null` gets an initials tile.

**Edit page text.** Edit the matching file in `content/pages/`. Placeholders like `{{news}}`, `{{team}}` and `{{publications}}` are filled in by the build.

## Deploying on GitHub Pages

1. Push this repository to GitHub.
2. In the repository go to **Settings > Pages**, choose **Deploy from a branch**, select `main` and `/ (root)`, and save.
3. The file `.nojekyll` (already included) tells GitHub Pages to serve the files as they are.

**Custom domain.** To serve the site at `neonatalnutritionresearch.com`, set the custom domain in **Settings > Pages** (GitHub then creates a `CNAME` file) and update the domain's DNS records as GitHub instructs. Until DNS is switched, the live GoDaddy site keeps working. If you publish to a project URL such as `user.github.io/repo-name/` instead, set `"basePath": "/repo-name"` in `content/site.json` so the 404 page finds its assets. Canonical links, the sitemap and the RSS feed use the `url` in `content/site.json`.

## Enabling the email sign-up and contact forms

A static site has no server to receive form submissions, so the **Subscribe** box on the home page and the **Drop us a line** form on the Contact page are hidden until you connect a form service. The Contact page shows the coordinators' phone number, address and hours in the meantime.

1. Create a form with a service such as [Formspree](https://formspree.io) or [Basin](https://usebasin.com) that accepts a JSON `POST` and returns a JSON response.
2. Put its endpoint URL in `formEndpoint` in `content/site.json`.
3. Run `python3 tools/build.py`. Both forms now appear and submit in the background.

To collect a mailing list you will need a service that actually manages subscribers (Buttondown, Mailchimp, ...); use its form-post URL as the endpoint.

## Differences from the GoDaddy site

- The members-only **MAGIC** page and the GoDaddy account/sign-in pages were not carried over; a static site cannot host a login.
- The cookie banner was removed because the rebuilt site sets no cookies and has no analytics. If you add analytics later, add a consent notice too.
- News posts keep their original URLs (`/f/<slug>/`) and dates.
- Added: publication search and topic filters, RSS (`feed.xml`), `sitemap.xml`, social-sharing metadata, and keyboard/screen-reader improvements.
- The **Frequently asked questions** card on the Resources page had no link on the original; it now points to the FAQ answers on the Maternal milk page.
- One broken link was corrected: the "cognitive impairment" study link on the Studies page used a malformed address (`http://10.1016/...`) and now points to the article's Journal of Pediatrics page. A typo in the team bio ("a a clinical research coordinator") was also fixed.

## Credits and licensing

- Fonts: [Mulish](https://fonts.google.com/specimen/Mulish) and [Quicksand](https://fonts.google.com/specimen/Quicksand), both under the SIL Open Font License 1.1.
- Photographs and figures were exported from the original site. Three images (`assets/img/resources/microbiome.jpg`, `assets/img/resources/faq.jpg` and `assets/img/posts/preterm-infant-incubator.jpg`) came from the website builder's built-in stock library, and several other photographs (the infant and clinician pictures on the home, milk and news pages) look like licensed stock imagery. Confirm the licence for each before publishing on a different host. Team portraits and research figures are presumably the team's own.
- Site content (c) Neonatal Nutrition Research. No open-source licence has been applied to the content; add one if you want to allow reuse.
