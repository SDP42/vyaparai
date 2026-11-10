# Purchase bills

Photograph or upload a supplier bill; the product reads it, you check it, and costs and supplier price changes stay current without typing.

## Flow

1. **Upload** a JPG, PNG, WebP or PDF (up to 10 MB). The same file is never added twice.
2. **Read**: a PDF with a text layer is read exactly (pypdf). Photos and scanned PDFs go through OCR: RapidOCR (PaddleOCR models on ONNX, CPU, about 1.5 s per bill) when installed, else Tesseract.
3. **Parse** into supplier, GSTIN, bill number, date (day-first), total and item lines. A line is "high" confidence when quantity x rate matches the printed amount; guessed lines are marked for checking. OCR often glues words and numbers ("GrandTotal13,061.58"); these are split before reading.
4. **Match** each line to a product in the workspace (token overlap plus string similarity, threshold 0.62). Unmatched lines are kept but change nothing.
5. **Review and edit** (draft): header, every line, product choice. The screen warns when lines do not add up to the bill total.
6. **Confirm**: only now does anything change. The product's unit cost is set from the newest confirmed bill, and the price history per product and supplier grows. A confirmed bill cannot be edited.

## Supplier price alert

When the latest confirmed price for a product is 5% or more above the one before, an alert "X now costs N% more to buy" appears (medium from 10%). It shows the selling price so the owner can see whether margin is covered, and it arrives before the rise shows up in sales margins.

## Safety

Size and pixel caps, no file name reaches a command, the OCR subprocess has a timeout, and PDFs are limited to 5 pages. Files are read in memory and not stored; the extracted text is kept on the draft.

## Limits

- Layouts vary. Tested on clean and OCR-glued text and a rendered bill image; **not yet measured on a collection of real bills**. Handwritten and heavily folded bills will need editing.
- Supplier names in capitals can lose their spaces in OCR; edit them on the review screen.
- GST is not split out; the rate paid is the printed rate per unit.
- Hindi bills: the OCR models and parser are tuned for English and numerals.

## API

`POST /workspaces/{id}/bills` · `GET .../bills` · `GET .../bills/{bill}` · `PUT .../bills/{bill}` · `POST .../bills/{bill}/confirm` · `DELETE .../bills/{bill}` (drafts) · `GET .../bills/prices/moves` · `GET .../bills/prices/{product}` · `GET .../bills/products` · `GET .../bills/engines`
