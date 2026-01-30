export interface DJTrack {
    id: string;
    title: string;
    price: string;
    isLocked: boolean;
}

export interface DJAlbum {
    id: string;
    title: string;
    isPremium: boolean;
}

export interface DJ {
    id: string;
    slug: string;
    name: string;
    genre: string[];
    image: string;
    banner?: string;
    bio: string;
    tracks: DJTrack[];
    albums: DJAlbum[];
}

export const MOCK_DJS: DJ[] = [
    {
        id: "1",
        slug: "dj-anish",
        name: "DJ Anish",
        genre: ["Techno", "House"],
        image: "https://images.unsplash.com/photo-1571266028243-e4733b0f0bb1?q=80&w=400&h=500&auto=format&fit=crop",
        banner: "https://images.unsplash.com/photo-1598387993441-a364f854c3e1?q=80&w=1200&h=400&auto=format&fit=crop",
        bio: "Techno visionary based in Bangalore. Focused on deep atmospheric sounds.",
        tracks: [
            { id: "t1", title: "Midnight Pulse", price: "₹49", isLocked: false },
            { id: "t2", title: "Eternal Echo", price: "₹99", isLocked: true },
            { id: "t3", title: "Void Walker", price: "₹149", isLocked: true },
        ],
        albums: [
            { id: "a1", title: "Solaris EP", isPremium: false },
            { id: "a2", title: "Dusk Theory (Full Pack)", isPremium: true },
        ]
    },
    {
        id: "2",
        slug: "sasha-vane",
        name: "Sasha Vane",
        genre: ["Deep House", "EDM"],
        image: "https://images.unsplash.com/photo-1594623121614-2909ac590859?q=80&w=400&h=500&auto=format&fit=crop",
        banner: "https://images.unsplash.com/photo-1574672280600-4accfa5b6f98?q=80&w=1200&h=400&auto=format&fit=crop",
        bio: "International EDM artist frequently touring Europe and Asia.",
        tracks: [
            { id: "s1", title: "Ocean Breeze", price: "₹79", isLocked: false },
            { id: "s2", title: "Neon Skyline", price: "₹129", isLocked: true },
        ],
        albums: [
            { id: "sa1", title: "Vortex Pack", isPremium: true },
        ]
    },
    {
        id: "3",
        slug: "arjun-pulse",
        name: "Arjun Pulse",
        genre: ["Indo House", "Bollywood Remix"],
        image: "https://images.unsplash.com/photo-1598387993281-cecf8368375d?q=80&w=400&h=500&auto=format&fit=crop",
        bio: "Mumbai's favorite for high-energy Bollywood remixes and deep house fusions.",
        tracks: [{ id: "ap1", title: "Desi Beat", price: "₹99", isLocked: false }],
        albums: []
    },
    { id: "4", slug: "mira-moon", name: "Mira Moon", genre: ["Melodic Techno"], image: "https://images.unsplash.com/photo-1574672280600-4accfa5b6f98?q=80&w=400&h=500&auto=format&fit=crop", bio: "Melodic sounds from the heart of Goa.", tracks: [], albums: [] },
    { id: "5", slug: "rohan-rex", name: "Rohan Rex", genre: ["PsyTrance", "Techno"], image: "https://images.unsplash.com/photo-1514525253361-b83f8b9627c5?q=80&w=400&h=500&auto=format&fit=crop", bio: "Psychedelic journeys.", tracks: [], albums: [] },
    { id: "6", slug: "neon-flux", name: "Neon Flux", genre: ["Cyberpunk", "Industrial"], image: "https://images.unsplash.com/photo-1459749411177-042180ce673c?q=80&w=400&h=500&auto=format&fit=crop", bio: "Futuristic beats.", tracks: [], albums: [] },
    { id: "7", slug: "dj-karan", name: "DJ Karan", genre: ["Hip-Hop", "Trap"], image: "https://images.unsplash.com/photo-1594623121614-2909ac590859?q=80&w=400&h=500&auto=format&fit=crop", bio: "Urban soundscape pioneer.", tracks: [], albums: [] },
    { id: "8", slug: "vicky-vibe", name: "Vicky Vibe", genre: ["Bollywood Remix", "Hip-Hop"], image: "https://images.unsplash.com/photo-1571266028243-e4733b0f0bb1?q=80&w=400&h=500&auto=format&fit=crop", bio: "Energy-packed sets.", tracks: [], albums: [] },
    { id: "9", slug: "luna-ray", name: "Luna Ray", genre: ["Techno"], image: "https://images.unsplash.com/photo-1514525253361-b83f8b9627c5?q=80&w=400&h=500&auto=format&fit=crop", bio: "Bright techno lights.", tracks: [], albums: [] },
    { id: "10", slug: "sonic-sam", name: "Sonic Sam", genre: ["EDM", "Techno"], image: "https://images.unsplash.com/photo-1459749411177-042180ce673c?q=80&w=400&h=500&auto=format&fit=crop", bio: "Sound waves specialist.", tracks: [], albums: [] },
    { id: "11", slug: "dj-ria", name: "DJ Ria", genre: ["House", "Deep House"], image: "https://images.unsplash.com/photo-1574672280600-4accfa5b6f98?q=80&w=400&h=500&auto=format&fit=crop", bio: "Deep grooves for late nights.", tracks: [], albums: [] },
    { id: "12", slug: "glitch-ghost", name: "Glitch Ghost", genre: ["Industrial", "Techno"], image: "https://images.unsplash.com/photo-1598387993281-cecf8368375d?q=80&w=400&h=500&auto=format&fit=crop", bio: "Ghostly industrial sounds.", tracks: [], albums: [] },
];
