import { motion } from "framer-motion";
import { LINKS } from "../config";
import screenshot from "../assets/screenshot.webp";
import flathubIcon from "../assets/flathub-dark.svg";
import GithubIcon from "../assets/github-light.svg";

export default function HeroSection({ version }) {
  return (
    <section className="relative flex flex-col items-center justify-center min-h-[70vh] pt-20 md:pt-24 pb-8 md:pb-12 w-full px-4 sm:px-6">
      {/* Badge */}
      <motion.a
        href={LINKS.flathub}
        target="_blank"
        rel="noopener noreferrer"
        className="mb-6 md:mb-8 px-4 py-1 mt-4 rounded-full bg-white/10 border border-white/20 backdrop-blur-lg text-xs sm:text-sm font-semibold text-pink-300 shadow inline-block text-center"
        whileHover={{ scale: 1.08, boxShadow: '0 0 8px 2px #f472b6, 0 0 12px 4px #a78bfa' }}
        whileTap={{ scale: 0.96 }}
        animate={{ y: [0, -4, 0], boxShadow: [
          '0 0 8px 1px #f472b6, 0 0 12px 4px #a78bfa',
          '0 0 12px 3px #f472b6, 0 0 16px 6px #a78bfa',
          '0 0 8px 1px #f472b6, 0 0 12px 4px #a78bfa'
        ] }}
        transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
      >
        {version ? `v${version} is now available 🚀` : "Loading version..."}
      </motion.a>

      
      {/* Headline */}
      <motion.h1
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="text-3xl sm:text-4xl md:text-6xl font-extrabold text-center mb-4 bg-gradient-to-r from-pink-400 via-fuchsia-400 to-purple-500 bg-clip-text text-transparent drop-shadow-lg"
      >
        Your Android's Best Friend on Linux
      </motion.h1>
      {/* Subheadline */}
      <motion.p
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-base sm:text-lg md:text-2xl text-gray-300 text-center max-w-2xl mb-8"
      >
        The definitive GTK4 application for seamless device management, wireless
        debugging, and low-latency screen mirroring.
      </motion.p>
      {/* CTA Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="flex flex-col sm:flex-row gap-3 sm:gap-4 mb-8 md:mb-12 w-full max-w-xl"
      >
        <motion.a
          href={LINKS.flathub}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 px-5 sm:px-7 py-3 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold text-base sm:text-lg shadow-xl hover:scale-105 transition-transform"
        >
          <img src={flathubIcon} alt="Flathub Icon" className="w-7 h-7 sm:w-8 sm:h-8" /> Download on Flathub
        </motion.a>
        <a
          href={LINKS.githubReleases}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 px-5 sm:px-7 py-3 rounded-xl bg-white/10 border border-white/20 backdrop-blur-lg text-white font-bold text-base sm:text-lg shadow-xl hover:scale-105 transition-transform"
        >
          <img src={GithubIcon} alt="Github Icon" className="w-7 h-7 sm:w-8 sm:h-8" /> Get it Github Releases
        </a>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, scale: 0.96, rotate: 0 }}
        animate={{ opacity: 1, scale: 1, rotate: 0 }}
        transition={{ delay: 0.5, type: 'spring', stiffness: 60 }}
        className="relative w-full max-w-3xl mx-auto rounded-2xl md:rounded-3xl overflow-hidden border border-white/20 bg-white/5 backdrop-blur-2xl shadow-2xl"
      >
        <div className="absolute -inset-2 rounded-3xl bg-gradient-to-br from-pink-500/30 via-purple-600/20 to-blue-700/20 blur-2xl z-0" />
        <img
          src={screenshot}
          alt="Aurynk App Screenshot"
          className="relative z-10 w-full object-cover rounded-3xl shadow-lg"
        />
      </motion.div>
    </section>
  );
}
