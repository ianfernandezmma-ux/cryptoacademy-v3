import { useEffect, useRef } from "react";

/** Looping ambient background video for a section. The parent needs the
 * `ca-ambient` class (position: relative + overflow: hidden); content inside
 * must sit in an element with position: relative to paint above the video. */
export default function Ambient({
  name,
  opacity = 0.45,
}: {
  name: "ambient-dust" | "ambient-dawn" | "ambient-stage";
  opacity?: number;
}) {
  const ref = useRef<HTMLVideoElement>(null);

  // Same autoplay hardening as the hero coin: retry after mount and on canplay.
  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    v.muted = true;
    const tryPlay = () => v.play().catch(() => {});
    tryPlay();
    v.addEventListener("canplay", tryPlay);
    return () => v.removeEventListener("canplay", tryPlay);
  }, []);

  const base = import.meta.env.BASE_URL;
  return (
    <>
      <video
        ref={ref}
        className="ca-ambient-video"
        style={{ opacity }}
        autoPlay
        muted
        loop
        playsInline
        poster={`${base}assets/${name}-poster.webp`}
        aria-hidden
      >
        <source src={`${base}assets/${name}.mp4`} type="video/mp4" />
      </video>
      <div className="ca-ambient-fade" />
    </>
  );
}
