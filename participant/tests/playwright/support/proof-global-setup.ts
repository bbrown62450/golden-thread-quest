import { existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";

import { PROOF_DIR } from "./proof";

/* Empties the folder evidence is captured into, before every run, so that what is in it afterwards is from that run. */
export default function emptyTheProofFolder() {
  mkdirSync(PROOF_DIR, { recursive: true });
  for (const name of readdirSync(PROOF_DIR)) if (/^(R\d+-[\w-]+\.(md|png)|run-output\.txt)$/.test(name) && existsSync(join(PROOF_DIR, name))) rmSync(join(PROOF_DIR, name));
}
