export type RiskSeviyesi = "normal" | "dikkat" | "kritik";

export interface Uyari {
  kod: string;
  seviye: "bilgi" | "dikkat" | "kritik";
  mesaj: string;
}

export interface SinifOlasiligi {
  sinif: string;
  olasilik: number;
}

export interface MorfolojiOzet {
  hucre_sayisi: number;
  kaplama_orani: number;
  ort_hucre_alani: number;
  ort_uzunluk: number;
  ort_genislik: number;
  ort_dairesellik: number;
  baskin_morfoloji: string;
  morfoloji_dagilimi: Record<string, number>;
}

export interface HucreOlcum {
  id: number;
  alan: number;
  uzunluk: number;
  genislik: number;
  dairesellik: number;
  en_boy_orani: number;
  morfoloji: string;
  merkez: [number, number];
  renk: [number, number, number];
}

export interface OnIslemeOzet {
  gurultu_azaltma: boolean;
  kontrast_iyilestirme: boolean;
  bulaniklik_skoru: number;
  parlaklik: number;
  orijinal_boyut: [number, number];
  segmentasyon_yontemi?: string;
  model_egitilmedi?: boolean;
}

export interface AnalizSonuc {
  id: number | null;
  numune_id: number | null;
  kare_indeksi: number;
  kare_zamani_sn: number;
  orijinal_gorsel: string;
  isaretli_gorsel: string;
  gradcam_gorsel: string | null;
  tahmin_sinifi: string;
  guven: number;
  desteklenmiyor: boolean;
  ilk_bes: SinifOlasiligi[];
  morfoloji: MorfolojiOzet;
  hucreler: HucreOlcum[];
  on_isleme: OnIslemeOzet;
  risk_seviyesi: RiskSeviyesi;
  uyarilar: Uyari[];
  aciklama: string;
  olusturulma: string | null;
}

export interface TopluSonuc {
  numune_id: number;
  toplam: number;
  basarili: number;
  hatali: number;
  sonuclar: AnalizSonuc[];
  ozet_aciklama: string;
}

export interface ZamanNoktasi {
  kare_indeksi: number;
  zaman_sn: number;
  hucre_sayisi: number;
  kaplama_orani: number;
  tahmin_sinifi: string;
  guven: number;
}

export interface VideoSonuc {
  numune_id: number;
  kare_araligi_sn: number;
  kare_sayisi: number;
  zaman_serisi: ZamanNoktasi[];
  seri_uyarilari: Uyari[];
  ozet_aciklama: string;
  kareler: AnalizSonuc[];
}

export interface GecmisKaydi {
  id: number;
  numune_id: number | null;
  tahmin_sinifi: string;
  guven: number;
  hucre_sayisi: number;
  risk_seviyesi: RiskSeviyesi;
  desteklenmiyor: boolean;
  olusturulma: string;
  isaretli_gorsel: string;
}

export interface AyarKaydi {
  anahtar: string;
  deger: number;
  aciklama: string;
}

export interface Saglik {
  durum: string;
  surum: string;
  cihaz: string;
  omnipose_hazir: boolean;
  siniflandirici_egitildi: boolean;
  segmentasyon_yontemi: string;
  desteklenen_sinif_sayisi: number;
}
