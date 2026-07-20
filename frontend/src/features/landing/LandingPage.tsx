import { Header } from "../../components/Header/Header";
import { Footer } from "../../components/Footer/Footer";
import { Hero } from "./components/Hero";
import { HowItWorks } from "./components/HowItWorks";
import { Differentiators } from "./components/Differentiators";
import { FinalCta } from "./components/FinalCta";

export default function LandingPage() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <HowItWorks />
        <Differentiators />
        <FinalCta />
      </main>
      <Footer />
    </>
  );
}
