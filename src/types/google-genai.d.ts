declare module "@google/genai" {
  export interface GoogleGenAIOptions {
    apiKey: string;
  }
  export class GoogleGenAI {
    constructor(opts: GoogleGenAIOptions);
    models: {
      generateContent(params: any): Promise<any>;
    };
  }
  export default GoogleGenAI;
}
