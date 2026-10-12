import Navbar from "../components/Navbar.jsx";
import Hero from "../components/Hero.jsx";
import Team from "../components/Team.jsx";
import Flow from "../components/Flow.jsx";
import Agents from "../components/Agents.jsx";
import Metrics from "../components/Metrics.jsx";
import Experiences from "../components/Experiences.jsx";
import Security from "../components/Security.jsx";
import CallToAction from "../components/CallToAction.jsx";
import Footer from "../components/Footer.jsx";

export default function Landing() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Team />
        <Flow />
        <Agents />
        <Metrics />
        <Experiences />
        <Security />
        <CallToAction />
      </main>
      <Footer />
    </>
  );
}
