import { hash as hashPassword } from '@node-rs/argon2';
import { randomBytes } from 'node:crypto';
import { PrismaClient } from '@prisma/client';

/**
 * Panele girebilen hiçbir yönetici kalmadığında yeni bir yönetici hesabı açar.
 *
 *     npm run create-admin --workspace=@berber/api -- ornek@example.com "Ad Soyad"
 *
 * Yalnızca DATABASE_URL gerekir (JWT vb. ayarlar aranmaz; uygulamanın env
 * doğrulamasını bilerek atlamak için kendi PrismaClient'ını kuruyor).
 *
 * Hesap "randevu almayan yönetici" olarak açılır: sitede, botta ve takvimde
 * berber olarak görünmez. Adres zaten kayıtlıysa o hesap yöneticiye
 * yükseltilir, açılır ve şifresi yenilenir. Şifre rastgele üretilir ve bir kez
 * ekrana basılır.
 */

const ARGON2_OPTIONS = { memoryCost: 19_456, timeCost: 2, parallelism: 1 } as const;

const prisma = new PrismaClient();

async function main(): Promise<void> {
  const email = process.argv[2]?.trim().toLowerCase();
  const name = process.argv[3]?.trim() || 'Yönetici';

  if (!email || !email.includes('@')) {
    console.error('Kullanım: npm run create-admin --workspace=@berber/api -- <e-posta> "<Ad Soyad>"');
    process.exit(1);
  }

  const shops = await prisma.shop.findMany({ take: 2 });
  if (shops.length !== 1) {
    console.error(`Tam olarak bir dükkan bekleniyordu, ${shops.length} bulundu.`);
    process.exit(1);
  }
  const shopId = shops[0]!.id;

  const password = randomBytes(12).toString('base64url');
  const passwordHash = await hashPassword(password, ARGON2_OPTIONS);

  const mevcut = await prisma.barber.findUnique({ where: { shopId_email: { shopId, email } } });

  if (mevcut) {
    await prisma.$transaction([
      prisma.barber.update({
        where: { id: mevcut.id },
        data: {
          role: 'admin',
          isActive: true,
          passwordHash,
          failedLoginCount: 0,
          lockedUntil: null,
        },
      }),
      prisma.refreshToken.updateMany({
        where: { barberId: mevcut.id, revokedAt: null },
        data: { revokedAt: new Date() },
      }),
    ]);
  } else {
    await prisma.barber.create({
      data: { shopId, name, email, role: 'admin', passwordHash, takesAppointments: false },
    });
  }

  console.log('\n' + '─'.repeat(62));
  console.log(`  ${mevcut ? 'Hesap güncellendi' : 'Yönetici hesabı açıldı'} — bu ekran bir daha gösterilmeyecek`);
  console.log('─'.repeat(62));
  console.log(`  Giriş adresi : ${email}`);
  console.log(`  Şifre        : ${password}`);
  console.log('─'.repeat(62));
  console.log('  Panele girdikten sonra Ayarlar’dan şifrenizi değiştirin.\n');
}

main()
  .catch((error: unknown) => {
    console.error('Yönetici hesabı açılamadı:');
    console.error(error);
    process.exit(1);
  })
  .finally(() => {
    void prisma.$disconnect();
  });
