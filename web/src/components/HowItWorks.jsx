import { motion as _motion } from "framer-motion";
import { Laptop, Scan, Smartphone, ArrowRight } from "lucide-react";

const steps = [
  {
    number: "01",
    title: "Open Aurynk",
    description: "Launch the application on your Linux desktop",
    icon: Laptop,
  },
  {
    number: "02",
    title: "Scan QR Code",
    description: "Use your phone camera to scan the pairing code",
    icon: Scan,
  },
  {
    number: "03",
    title: "Control your device",
    description: "Start mirroring, transferring files, and more",
    icon: Smartphone,
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="relative px-4 py-16">
      <div className="max-w-6xl mx-auto">
        {/* Section Title */}
        <_motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2
            className="text-4xl md:text-5xl mb-4 text-[#ec4899]"
            style={{ fontWeight: 700 }}
          >
            Get started in seconds
          </h2>
          <p className="text-gray-400 text-lg">
            No complicated setup. Just three simple steps.
          </p>
        </_motion.div>
        {/* Steps */}
        <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <div
                key={step.number}
                className="flex items-center gap-4 md:gap-8"
              >
                <_motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.2 }}
                  whileHover={{ scale: 1.05, y: -5 }}
                  className="backdrop-blur-xl bg-[#1a1a2e]/40 border border-white/10 rounded-2xl p-8 hover:bg-[#1a1a2e]/60 hover:border-pink-500/30 transition-all duration-300 group w-full md:w-64 flex flex-col items-center justify-center"
                >
                  {/* Step number */}
                  <div className="text-pink-500/50 text-xl font-bold  mb-4">
                    {step.number}
                  </div>
                  {/* Icon */}
                  <div className="flex justify-center p-4 rounded-xl mb-6 bg-gradient-to-br from-pink-600 to-fuchsia-600 group-hover:scale-110 transition-transform duration-300">
                    <Icon className="w-8 h-8 text-white" />
                  </div>
                  {/* Content */}
                  <h3 className="text-xl mb-2 text-white text-center">
                    {step.title}
                  </h3>
                  <p className="text-gray-400 text-sm text-center">
                    {step.description}
                  </p>
                </_motion.div>
                {/* Arrow connector */}
                {index < steps.length - 1 && (
                  <_motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: index * 0.2 + 0.3 }}
                    className="hidden md:block"
                  >
                    <ArrowRight className="w-6 h-6 text-white/30" />
                  </_motion.div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
