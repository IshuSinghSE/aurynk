import { motion } from "framer-motion";
import { Star } from "lucide-react";
import logo from "../assets/logo.webp";

const AmbientOrbs = () => {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-[-1]">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-[120px] animate-float" />
      <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-pink-500/20 rounded-full blur-[100px] animate-float-delayed" />
      <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/20 rounded-full blur-[90px] animate-float" />
    </div>
  );
};

const Navbar = () => {
  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="fixed top-4 left-0 w-full z-50"
    >
      <AmbientOrbs />
      <div className="max-w-6xl mx-auto backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl py-2 md:py-3 px-3 md:px-6 relative w-full">
        <div className="grid grid-cols-3 items-center gap-2 md:gap-4">
          {/* Left: Logo */}
          <div className="flex items-center gap-1 md:gap-2 min-w-0">
            <img src={logo} alt="Aurynk Logo" className="w-12 h-12 rounded-lg" />
            <span className="text-base sm:text-xl font-bold bg-gradient-pink-purple bg-clip-text text-transparent truncate">
              Aurynk
            </span>
          </div>

          {/* Center: Navigation Links */}
          <div className="hidden md:flex items-center justify-center gap-4 md:gap-8">
            <a
              href="#features"
              className="text-md text-foreground/80 hover:text-foreground transition-colors"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-md text-foreground/80 hover:text-foreground transition-colors"
            >
              How it Works
            </a>
            <a
              href="https://github.com/IshuSinghSE/aurynk"
              target="_blank"
              rel="noopener noreferrer"
              className="text-md text-foreground/80 hover:text-foreground transition-colors"
            >
              GitHub
            </a>
          </div>

          {/* Right: CTA Button */}
          <div className="flex justify-end min-w-0">
            <a
              href="https://github.com/IshuSinghSE/aurynk"
              target="_blank"
              rel="noopener noreferrer"
            >
              <button className="backdrop-blur-xl bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg px-4 py-2 flex items-center text-sm font-semibold text-white shadow-md hover:shadow-lg transition">
                <Star className="w-4 h-4 mr-2" />
                Star on GitHub
              </button>
            </a>
          </div>
        </div>
      </div>
    </motion.nav>
  );
};
export default Navbar;
