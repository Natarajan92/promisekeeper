import { isolatedServer } from "./server";

export default async function setup() {
  const server=await isolatedServer(19000);
  await server.start();
  return async()=>server.stop();
}
