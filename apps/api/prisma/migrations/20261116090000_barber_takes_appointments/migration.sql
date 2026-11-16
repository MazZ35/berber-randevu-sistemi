-- Randevu almayan yönetici hesapları (müşteriye berber olarak görünmez).
ALTER TABLE "barbers" ADD COLUMN "takes_appointments" BOOLEAN NOT NULL DEFAULT true;
