

# Aurynk Landing Page
<p align="center">
<a href="http://ishusinghse.github.io/aurynk/" target="_blank" rel="noopener noreferrer">
	<img src="../data/icons/io.github.IshuSinghSE.aurynk.png" alt="Aurynk Logo" width="128" height="128" style="vertical-align:middle; margin-bottom: 0.5em;" />
</a>
</p>

>This is the official landing page for [Aurynk](https://github.com/IshuSinghSE/aurynk), a modern open-source Linux application for Android device management, built with React, Vite, Tailwind CSS, and Framer Motion.

## ✨ Features

- **Glassmorphic, animated UI**: Deep Space Glass design with ambient orbs and glass cards
- **Responsive**: Looks great on all devices
- **Dynamic version badge**: Fetches latest release from GitHub
- **Bento grid**: Showcases all major features
- **How it Works**: Step-by-step animated guide
- **Call to Action**: Prominent Flathub download button
- **Minimal glass footer**: Social and project links

## 🚀 Tech Stack

- [React](https://react.dev/) + [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Framer Motion](https://www.framer.com/motion/)
- [Lucide Icons](https://lucide.dev/)

## 🛠️ Development

### Install dependencies

```bash
npm install
# or
yarn install
```

### Start the dev server

```bash
npm run dev
# or
yarn dev
```

Visit [http://localhost:5173/aurynk/](http://localhost:5173/aurynk/) in your browser.

### Build for production

```bash
npm run build
# or
yarn build
```

### Lint & Fix

```bash
npm run lint
# or
bunx eslint src --fix
```

## 📁 Project Structure

- `src/` — Main source code
	- `components/` — React components (Navbar, HeroSection, FeaturesBento, HowItWorks, Footer, etc.)
	- `assets/` — Images and SVGs imported in code
	- `config.js` — Centralized config for links
- `public/` — Static assets (if needed for direct URL access)

## 📝 Customization

- Update links in `src/config.js` for easy maintenance
- Add or modify features in `src/components/FeaturesBento.jsx`

## 🧑‍💻 Contributing

Pull requests and issues are welcome! See the [main Aurynk repo](https://github.com/IshuSinghSE/aurynk) for more.

---

© 2025 Aurynk. Open Source under GPL-3.0.
