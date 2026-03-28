// Inicializácia MongoDB pre UniFi Network Application
// Spúšťa sa automaticky pri prvom štarte unifi-db kontajnera

db = db.getSiblingDB("unifi");
db.createUser({
  user: process.env.MONGO_INITDB_ROOT_USERNAME,
  pwd:  process.env.MONGO_INITDB_ROOT_PASSWORD,
  roles: [{ role: "dbOwner", db: "unifi" }]
});
