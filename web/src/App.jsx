import AnimatedOrbs from "./components/AnimatedOrbs";
import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import { useEffect, useState } from "react";
import FeaturesBento from "./components/FeaturesBento";
import { LINKS } from "./config";
import HowItWorks from "./components/HowItWorks";
import Footer from "./components/Footer";

function App() {
  const [version, setVersion] = useState(null);

  useEffect(() => {
    async function fetchVersion() {
      try {
        const res = await fetch(
          "https://api.github.com/repos/IshuSinghSE/aurynk/releases/latest"
        );
        const data = await res.json();
        if (data && data.tag_name) {
          setVersion(data.tag_name.replace(/^v/, ""));
        }
      } catch (e) {
        setVersion(null);
        console.error("Failed to fetch version:", e);
      }
    }
    fetchVersion();
  }, []);

  return (
    <div className="min-h-screen bg-[#0f0f12] text-white font-sans relative overflow-x-hidden">
      <AnimatedOrbs />
      <Navbar />
      <HeroSection version={version} />
      <FeaturesBento />
      <HowItWorks />
      <Footer />
    </div>
  );
}

export default App;
