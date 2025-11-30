import { GanttChart, Upload, Volume2, Wifi, Zap } from "lucide-react";
import { motion as _motion } from "framer-motion";

const features = [
  {
    title: "Wireless Debugging",
    desc: "Ditch the cable. Pair instantly via QR code.",
    icon: <Wifi className="w-8 h-8 text-purple-400" />,
    cardClass: "md:row-span-2 md:col-span-2",
  },
  {
    title: "Low-Latency Mirroring",
    desc: "Powered by scrcpy. 60fps+ performance.",
    icon: <Zap className="w-8 h-8 text-purple-400" />,
    cardClass: "",
  },
  {
    title: "Native GTK4",
    desc: "Designed for modern GNOME. Looks native on Ubuntu/Fedora.",
    icon: <GanttChart className="w-8 h-8 text-blue-400" />,
    cardClass: "",
  },
  {
    title: "File Transfer",
    desc: "Drag and drop files between PC and Phone.",
    icon: <Upload className="w-8 h-8 text-fuchsia-400" />,
    cardClass: "",
  },
  {
    title: "Audio Forwarding",
    desc: "Stream phone audio to your PC speakers.",
    icon: <Volume2 className="w-8 h-8 text-cyan-400" />,
    cardClass: "",
  },
];

export default function FeaturesBento() {
  return (
    <section id="features" className="relative py-16 md:py-24 px-4 sm:px-6 max-w-6xl mx-auto w-full">
      <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-center mb-10 md:mb-14 bg-gradient-to-r from-pink-400 via-fuchsia-400 to-purple-500 bg-clip-text text-transparent">
        Everything you need, nothing you don't.
      </h2>
      <div className="hidden md:grid grid-cols-3 grid-rows-2 gap-6 auto-rows-[minmax(180px,1fr)]">
        {/* Main feature: large card, left column, spans 2 rows */}
        <_motion.div
          key={features[0].title}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="relative rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-lg p-7 flex flex-col gap-4 row-span-2 col-span-1 overflow-hidden"
        >
          {/* Glow effect */}
          <div className="absolute inset-0 rounded-2xl pointer-events-none z-0" style={{background: 'radial-gradient(ellipse at 40% 40%, rgba(168,85,247,0.18) 0%, rgba(236,72,153,0.10) 60%, transparent 100%)'}} />
          <div className="relative z-10 flex items-center mb-2">{features[0].icon}</div>
          <div className="relative z-10 font-bold text-xl md:text-2xl text-white mb-1">{features[0].title}</div>
          <div className="relative z-10 text-gray-300 text-base md:text-lg">{features[0].desc}</div>
        </_motion.div>
        {/* Top row, center and right */}
        <_motion.div
          key={features[1].title}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.18 }}
          className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow p-6 flex flex-col gap-3 col-span-1 row-span-1"
        >
          <div className="flex items-center">{features[1].icon}</div>
          <div className="font-bold text-lg text-white mb-1">{features[1].title}</div>
          <div className="text-gray-300 text-base">{features[1].desc}</div>
        </_motion.div>
        <_motion.div
          key={features[2].title}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.22 }}
          className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow p-6 flex flex-col gap-3 col-span-1 row-span-1"
        >
          <div className="flex items-center">{features[2].icon}</div>
          <div className="font-bold text-lg text-white mb-1">{features[2].title}</div>
          <div className="text-gray-300 text-base">{features[2].desc}</div>
        </_motion.div>
        {/* Bottom row, center and right */}
        <_motion.div
          key={features[3].title}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.26 }}
          className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow p-6 flex flex-col gap-3 col-span-1 row-span-1"
        >
          <div className="flex items-center">{features[3].icon}</div>
          <div className="font-bold text-lg text-white mb-1">{features[3].title}</div>
          <div className="text-gray-300 text-base">{features[3].desc}</div>
        </_motion.div>
        <_motion.div
          key={features[4].title}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.34 }}
          className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow p-6 flex flex-col gap-3 col-span-1 row-span-1"
        >
          <div className="flex items-center">{features[4].icon}</div>
          <div className="font-bold text-lg text-white mb-1">{features[4].title}</div>
          <div className="text-gray-300 text-base">{features[4].desc}</div>
        </_motion.div>
      </div>
      {/* Mobile/tablet: fallback to simple grid */}
      <div className="md:hidden grid grid-cols-1 sm:grid-cols-2 gap-4 auto-rows-[minmax(160px,1fr)]">
        {features.map((f, i) => (
          <_motion.div
            key={f.title}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 + i * 0.08 }}
            className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow p-5 flex flex-col gap-3"
          >
            <div className="flex items-center">{f.icon}</div>
            <div className="font-bold text-base sm:text-lg text-white mb-1">{f.title}</div>
            <div className="text-gray-300 text-sm sm:text-base">{f.desc}</div>
          </_motion.div>
        ))}
      </div>
    </section>
  );
}
