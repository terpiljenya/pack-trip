import OpenAI from 'openai';

// the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
const openai = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true
});

export async function generateItineraryImage(
  title: string,
  description: string,
  destination: string
): Promise<string | null> {
  try {
    const prompt = `Create a beautiful, vibrant travel destination image for "${title}" in ${destination}. ${description}. Make it look like a professional travel brochure photo showing the key highlights and atmosphere of this itinerary. Focus on the destination's iconic landmarks, scenery, and activities. High quality, colorful, inviting travel photography style.`;

    const response = await openai.images.generate({
      model: 'dall-e-3',
      prompt: prompt,
      n: 1,
      size: '1024x1024',
      quality: 'standard',
    });

    return response.data[0].url || null;
  } catch (error) {
    console.error('Error generating AI image:', error);
    return null;
  }
}