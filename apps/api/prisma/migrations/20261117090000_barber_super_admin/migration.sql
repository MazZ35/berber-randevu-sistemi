-- Gizli hesap yerine görünür "süper yönetici". Mevcut işaretli hesaplar korunur.
ALTER TABLE "barbers" RENAME COLUMN "is_hidden" TO "is_super_admin";
