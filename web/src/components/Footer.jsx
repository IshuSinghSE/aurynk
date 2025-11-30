import { Github, MessageCircle, BookOpen } from "lucide-react";

export default function Footer() {
  return (
    <footer className="w-full py-4 border-t border-white/10 bg-white/5 backdrop-blur-xl text-center text-gray-400 text-xs sm:text-sm flex flex-col items-center gap-2 px-2">
      <div>© 2025 Aurynk. Open Source under GPL-3.0.</div>
      <div className="flex gap-6 justify-center">
        <a
          href="https://github.com/IshuSinghSE/aurynk"
          className="hover:text-pink-400 transition-colors flex items-center gap-1"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Github className="w-4 h-4" /> GitHub
        </a>
        <a
          href="https://github.com/IshuSinghSE/aurynk/issues"
          className="hover:text-pink-400 transition-colors flex items-center gap-1"
          target="_blank"
          rel="noopener noreferrer"
        >
          <MessageCircle className="w-4 h-4" /> Issues
        </a>
        <a
          href="https://github.com/IshuSinghSE/aurynk/discussions"
          className="hover:text-pink-400 transition-colors flex items-center gap-1"
          target="_blank"
          rel="noopener noreferrer"
        >
          <BookOpen className="w-4 h-4" /> Discussions
        </a>
      </div>
    </footer>
  );
}
