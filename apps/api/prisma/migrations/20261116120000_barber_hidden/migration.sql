-- Gizli (üst yönetici) hesaplar: diğer yöneticilere görünmez.
ALTER TABLE "barbers" ADD COLUMN "is_hidden" BOOLEAN NOT NULL DEFAULT false;
