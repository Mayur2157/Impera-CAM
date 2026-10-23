import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import { setToken } from "@/api/token";

afterEach(() => {
  cleanup();
  setToken(null); // the token module also keeps a copy in memory
  sessionStorage.clear();
});
