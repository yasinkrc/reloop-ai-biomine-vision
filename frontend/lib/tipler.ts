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

// --- CRISPR-Cas / genom ---
export interface CrisprDizisi {
  kontig: string;
  baslangic: number;
  bitis: number;
  tekrar_uzunlugu: number;
  tekrar_konsensus: string;
  tekrar_sayisi: number;
  aralayici_sayisi: number;
  aralayicilar: string[];
  ortalama_aralayici_uzunlugu: number;
  tekrar_kimlik_yuzdesi: number;
}

export interface CasGeni {
  kontig: string;
  baslangic: number;
  bitis: number;
  yon: string;
  ad: string;
  kaynak: string;
}

export interface GenomSonuc {
  dosya_adi: string;
  kontig_sayisi: number;
  toplam_uzunluk: number;
  gc_yuzdesi: number;
  yontem_crispr: string;
  yontem_tur: string;
  crispr_cas_tipi: string;
  toplam_aralayici: number;
  diziler: CrisprDizisi[];
  cas_genleri: CasGeni[];
  tur_eslesmesi: {
    tur: string;
    ani_yuzdesi: number;
    hizalanan_kesir: number;
    referans: string;
  } | null;
  genom_haritasi: string | null;
  lokus_haritasi: string | null;
  html_rapor: string | null;
  pdf_rapor: string | null;
  csv_rapor: string | null;
  json_rapor: string | null;
  aciklama: string;
  uyarilar: string[];
  // Çoklu genom
  genom_sayisi: number;
  karsilastirmali: boolean;
  hizalama_sayisi: number;
  karsilastirma_html: string | null;
  genomlar: GenomOzet[];
}

export interface GenomOzet {
  ad: string;
  kontig_sayisi: number;
  toplam_uzunluk: number;
  gc_yuzdesi: number;
  gen_sayisi: number;
  gen_kaynagi: string;
  crispr_dizisi: number;
  toplam_aralayici: number;
  cas_gen_adayi: number;
  tur_eslesmesi: {
    tur: string;
    ani_yuzdesi: number;
    hizalanan_kesir: number;
    referans: string;
  } | null;
  diziler: CrisprDizisi[];
}

// --- Hücre takibi ---
export interface TakipZamanNoktasi {
  kare: number;
  zaman_sn: number;
  hucre_sayisi: number;
  aktif_iz: number;
}

export interface Iz {
  id: number;
  parent_id: number | null;
  baslangic_kare: number;
  bitis_kare: number;
  sure_kare: number;
  noktalar: { kare: number; zaman_sn: number; x: number; y: number; alan: number }[];
}

export interface Bolunme {
  kare: number;
  zaman_sn: number;
  parent: number;
  cocuklar: number[];
}

export interface TakipSonuc {
  dosya_adi: string;
  kare_sayisi: number;
  kare_araligi_sn: number;
  yontem: string;
  iz_sayisi: number;
  ham_iz_parcasi: number;
  uzun_iz_sayisi: number;
  bolunme_sayisi: number;
  ilk_kare_hucre: number;
  son_kare_hucre: number;
  kaplama_kareler: string[];
  kaplama_video: string | null;
  kaplama_gif: string | null;
  grafik: string | null;
  zaman_serisi: TakipZamanNoktasi[];
  izler: Iz[];
  bolunmeler: Bolunme[];
  aciklama: string;
  csv_rapor: string | null;
  json_rapor: string | null;
}
