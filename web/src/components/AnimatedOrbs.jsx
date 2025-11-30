import { motion as _motion } from 'framer-motion';

// AnimatedOrbs: full-screen animated gradient orbs for background
export default function AnimatedOrbs() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Pink orb */}
      <_motion.div
        className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-gradient-to-br from-pink-500 via-fuchsia-500 to-purple-700 opacity-40 blur-3xl"
        animate={{
          x: [0, 60, 0],
          y: [0, 40, 0],
        }}
        transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
      />
      {/* Blue orb */}
      <_motion.div
        className="absolute bottom-[-15%] right-[-10%] w-[35vw] h-[35vw] rounded-full bg-gradient-to-br from-blue-700 via-indigo-600 to-purple-700 opacity-30 blur-3xl"
        animate={{
          x: [0, -40, 0],
          y: [0, -30, 0],
        }}
        transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut' }}
      />
      {/* Purple orb */}
      <_motion.div
        className="absolute top-[30%] left-[60%] w-[30vw] h-[30vw] rounded-full bg-gradient-to-br from-purple-700 via-pink-500 to-fuchsia-500 opacity-25 blur-2xl"
        animate={{
          x: [0, 30, 0],
          y: [0, 50, 0],
        }}
        transition={{ duration: 26, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  );
}
