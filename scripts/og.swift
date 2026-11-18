// Open Graph card for every page (1200×630 PNG): the eye mark from assets/favicon.svg, the name, the hero line and
// a short fact line. Text is fixed here; change it together with the landing page hero.
//
//   swiftc -O scripts/og.swift -o /tmp/icgor-og && /tmp/icgor-og assets/og.png
import Foundation
import CoreGraphics
import CoreText
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 2 else { print("usage: og <out.png>"); exit(1) }
let W: CGFloat = 1200, H: CGFloat = 630
let sRGB = CGColorSpace(name: CGColorSpace.sRGB)!

func color(_ hex: String, _ alpha: CGFloat = 1) -> CGColor {
    var v: UInt64 = 0
    Scanner(string: String(hex.dropFirst())).scanHexInt64(&v)
    return CGColor(red: CGFloat((v >> 16) & 255) / 255, green: CGFloat((v >> 8) & 255) / 255,
                   blue: CGFloat(v & 255) / 255, alpha: alpha)
}
// Brand colours (assets/favicon.svg).
let brand = "#0D4A4C", paper = "#F5F6F4", sand = "#D9C7A3"

let ctx = CGContext(data: nil, width: Int(W), height: Int(H), bitsPerComponent: 8, bytesPerRow: 0, space: sRGB,
                    bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
ctx.setFillColor(color(brand)); ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
ctx.translateBy(x: 0, y: H); ctx.scaleBy(x: 1, y: -1)  // top-left origin

// Eye mark, favicon geometry (48-unit box) scaled 7×, centred at (930, 315).
ctx.saveGState()
ctx.translateBy(x: 762, y: 147); ctx.scaleBy(x: 7, y: 7)
let eye = CGMutablePath()
eye.move(to: CGPoint(x: 7, y: 24))
eye.addCurve(to: CGPoint(x: 41, y: 24), control1: CGPoint(x: 13, y: 12.5), control2: CGPoint(x: 35, y: 12.5))
eye.addCurve(to: CGPoint(x: 7, y: 24), control1: CGPoint(x: 35, y: 35.5), control2: CGPoint(x: 13, y: 35.5))
eye.closeSubpath()
ctx.addPath(eye); ctx.setStrokeColor(color(paper)); ctx.setLineWidth(3); ctx.setLineJoin(.round); ctx.strokePath()
ctx.setFillColor(color(sand)); ctx.fillEllipse(in: CGRect(x: 24 - 6.6, y: 24 - 6.6, width: 13.2, height: 13.2))
ctx.setFillColor(color(brand)); ctx.fillEllipse(in: CGRect(x: 24 - 2.9, y: 24 - 2.9, width: 5.8, height: 5.8))
ctx.restoreGState()

func font(_ names: [String], _ size: CGFloat) -> CTFont {
    for name in names {
        let f = CTFontCreateWithName(name as CFString, size, nil)
        if (CTFontCopyPostScriptName(f) as String) == name { return f }
    }
    return CTFontCreateUIFontForLanguage(.system, size, "tr" as CFString)!
}
func text(_ s: String, _ f: CTFont, _ hex: String, x: CGFloat, baseline: CGFloat, maxWidth: CGFloat) {
    var size = CTFontGetSize(f)
    var line: CTLine
    repeat {
        let attr = NSAttributedString(string: s, attributes: [
            NSAttributedString.Key(kCTFontAttributeName as String): CTFontCreateCopyWithAttributes(f, size, nil, nil),
            NSAttributedString.Key(kCTForegroundColorAttributeName as String): color(hex),
        ])
        line = CTLineCreateWithAttributedString(attr)
        size *= 0.97
    } while CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil)) > maxWidth && size > 20
    ctx.saveGState()
    ctx.translateBy(x: x, y: baseline); ctx.scaleBy(x: 1, y: -1)
    ctx.textPosition = .zero
    CTLineDraw(line, ctx)
    ctx.restoreGState()
}
let serif = ["NewYorkLarge-Semibold", "NewYork-Semibold", "Georgia-Bold"]
let sans = ["SFPro-Medium", ".SFNS-Medium", "HelveticaNeue-Medium"]
text("İçgör", font(serif, 132), paper, x: 80, baseline: 250, maxWidth: 640)
text("İçini gör.", font(serif, 64), sand, x: 84, baseline: 340, maxWidth: 640)
text("Barkodu okut: katkı maddeleri, 14 alerjen", font(sans, 32), paper, x: 86, baseline: 430, maxWidth: 640)
text("ve Beslenme Skoru, ailedeki her kişiye ayrı.", font(sans, 32), paper, x: 86, baseline: 474, maxWidth: 640)
text("iPhone · Türkçe · Hesap yok, reklam yok", font(sans, 24), sand, x: 86, baseline: 552, maxWidth: 640)

let out = URL(fileURLWithPath: args[1])
let dest = CGImageDestinationCreateWithURL(out as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
guard CGImageDestinationFinalize(dest) else { fatalError("cannot write \(out.path)") }
print("\(out.lastPathComponent) \(Int(W))×\(Int(H))")
