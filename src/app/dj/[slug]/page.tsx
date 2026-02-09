import { djs } from '@/app/lib/mock-djs';
import TrackCard from '@/app/components/TrackCard';
import Image from 'next/image';

export default function DJProfilePage({ params }: { params: { slug: string } }) {
  const dj = djs.find((d) => d.slug === params.slug);

  if (!dj) {
    return <div className="text-white text-center p-8">DJ not found</div>;
  }

  return (
    <main className="p-8 text-white">
      <div className="flex flex-col md:flex-row items-center md:items-start gap-8 mb-8">
        <div className="w-48 h-48 relative rounded-full overflow-hidden shadow-lg">
          <Image src={dj.image} alt={dj.name} layout="fill" objectFit="cover" />
        </div>
        <div className="text-center md:text-left">
          <h1 className="text-5xl font-bold font-display text-mint-primary">{dj.name}</h1>
          <p className="text-mint-accent text-lg mt-2">{dj.genre.join(', ')}</p>
          <p className="mt-4 max-w-lg text-mint-studio">{dj.bio}</p>
        </div>
      </div>

      <div>
        <h2 className="text-3xl font-bold font-display mb-6 text-mint-primary">Releases</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {/* Mock data for now */}
          <TrackCard tier="single" title="Sunset Groove" artist={dj.name} />
          <TrackCard tier="zip" title="Midnight Drive EP" artist={dj.name} />
          <TrackCard tier="fan" title="Exclusive Bootleg" artist={dj.name} />
        </div>
      </div>
    </main>
  );
}
