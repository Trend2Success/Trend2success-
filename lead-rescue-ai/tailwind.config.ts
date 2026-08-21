import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#38BDF8",
          light: "#7DD3FC",
          dark: "#081523",
          darker: "#040D16",
        },
      },
    },
  },
  plugins: [],
};

export default config;
