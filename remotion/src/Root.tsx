import { ReelComposition } from "./reel/Reel";
import { StudioComposition } from "./studio/Studio";

// Remotion faqat video uchun. Posterlar va Reels muqovalari Figma'da yaratiladi (scripts/poster_studio.py), artwork — Google Flow.
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <ReelComposition />
      <StudioComposition />
    </>
  );
};
