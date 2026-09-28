"""SaPo Shop - PyQt5 GUI (pip install PyQt5)"""
import os
import sys
import sqlite3
from datetime import date, timedelta

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont, QTextDocument
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDateEdit, QDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, QDialogButtonBox,
)

DB_PATH = "sapo_stockfinal.db"
CATEGORIES = ["vegetable", "fruit", "bakery", "foodstuff", "drinks",
              "alcohol", "sweets", "misc", "salty snacks"]
# column positions in the stock table (same as your console version)
CODE, NAME, PRICE, TYPE, QTY, BB = 0, 1, 2, 3, 5, 7
EXPIRED, SOON = QColor(255, 190, 190), QColor(255, 230, 170)


# ---------------------------------------------------------------- helpers
def parse_date(s):
    try:
        return date.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None


def item_price(it):
    if it["type"] == "per kg":
        return round(it["unit_price"] / 1000 * it["amount"], 2)
    return round(it["unit_price"], 2)


def build_receipt(cart):
    w = 32
    lines = ["SaPo market".center(w), str(date.today()).center(w), "=" * w]
    total = 0.0
    for it in cart:
        p = item_price(it)
        total += p
        amount = f"{it['amount']} g" if it["type"] == "per kg" else "x1"
        lines += [it["name"], f"  {amount}".ljust(22) + f"${p:>9.2f}", "-" * w]
    lines += ["=" * w, "TOTAL".ljust(22) + f"${total:>9.2f}"]
    return "\n".join(lines)


def print_text(text, parent):
    printer = QPrinter(QPrinter.HighResolution)
    if QPrintDialog(printer, parent).exec_() == QDialog.Accepted:
        doc = QTextDocument()
        doc.setDefaultFont(QFont("Courier New", 10))
        doc.setPlainText(text)
        doc.print_(printer)


def next_codes(existing, n):
    parsed = []
    for c in existing:
        prefix, sep, suffix = c.rpartition("I")
        if sep and suffix.isdigit():
            parsed.append((prefix, len(suffix), int(suffix)))
    if not parsed:
        raise ValueError("Could not read the existing product codes.")
    prefix, width, _ = parsed[0]
    top = max(p[2] for p in parsed)
    return [f"{prefix}I{str(top + i).zfill(width)}" for i in range(1, n + 1)]


def make_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for i in range(1, len(headers)):
        t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
    return t


def fill_table(t, headers, data, colors=None):
    t.setHorizontalHeaderLabels(headers)
    t.setRowCount(len(data))
    for r, row in enumerate(data):
        for c, v in enumerate(row):
            item = QTableWidgetItem(str(v))
            if c > 0:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if colors and colors[r]:
                item.setBackground(colors[r])
                item.setForeground(QColor(0, 0, 0))
            t.setItem(r, c, item)


# --------------------------------------------------------------- database
class StockDB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.cols = [r[1] for r in self.conn.execute("PRAGMA table_info(stock)")]
        if len(self.cols) < 8:
            raise RuntimeError("Table 'stock' not found or has unexpected columns.")
        self.qty_col = self.cols[QTY]

    def by_code(self, code):
        return self.conn.execute("SELECT * FROM stock WHERE code = ?", (code,)).fetchone()

    def by_product_id(self, pid):
        return self.conn.execute(
            "SELECT * FROM stock WHERE product_id = ? ORDER BY best_before_date ASC",
            (pid,)).fetchall()

    def by_category(self, cat):
        return self.conn.execute("SELECT * FROM stock WHERE category = ?", (cat,)).fetchall()

    def change_kg(self, code, delta):
        self.conn.execute(
            f"UPDATE stock SET {self.qty_col} = {self.qty_col} + ? WHERE code = ?", (delta, code))

    def delete(self, code):
        self.conn.execute("DELETE FROM stock WHERE code = ?", (code,))

    def insert(self, row):
        ph = ", ".join("?" for _ in self.cols)
        self.conn.execute(f"INSERT INTO stock ({', '.join(self.cols)}) VALUES ({ph})", list(row))

    def commit(self):
        self.conn.commit()


# ---------------------------------------------------------------- dialogs
class ReceiptDialog(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Receipt")
        self.resize(420, 520)
        self.print_requested = False
        lay = QVBoxLayout(self)
        view = QPlainTextEdit(text)
        view.setReadOnly(True)
        view.setFont(QFont("Courier New", 11))
        lay.addWidget(view)
        row = QHBoxLayout()
        for label, printing in (("Complete sale", False), ("Complete and print", True)):
            b = QPushButton(label)
            b.clicked.connect(lambda _, p=printing: self.finish(p))
            row.addWidget(b)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        lay.addLayout(row)

    def finish(self, printing):
        self.print_requested = printing
        self.accept()


class RestockDialog(QDialog):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Restock {name}")
        form = QFormLayout(self)
        self.units = QSpinBox()
        self.units.setRange(1, 10000)
        self.bb = QDateEdit(QDate.currentDate().addDays(30))
        self.bb.setCalendarPopup(True)
        self.bb.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Units to add:", self.units)
        form.addRow("Best before:", self.bb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def values(self):
        return self.units.value(), self.bb.date().toString("yyyy-MM-dd")


class UnitsDialog(QDialog):
    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Units of {rows[0][NAME]}")
        self.resize(420, 350)
        lay = QVBoxLayout(self)
        t = make_table(["Code", "Price", "Best before"])
        fill_table(t, ["Code", "Price", "Best before"],
                   [[r[CODE], f"${float(r[PRICE]):.2f}", r[BB]] for r in rows])
        lay.addWidget(t)


# ------------------------------------------------------------ main window
class MainWindow(QMainWindow):
    def __init__(self, stock):
        super().__init__()
        self.stock = stock
        self.cart = []
        self.catalog_groups = []
        self.cat_type = None
        self.setWindowTitle("SaPo Shop")
        self.resize(820, 600)
        tabs = QTabWidget()
        tabs.addTab(self.build_shop_tab(), "Shop")
        tabs.addTab(self.build_catalog_tab(), "Catalog")
        self.setCentralWidget(tabs)
        self.load_catalog()
        self.scan_input.setFocus()

    # ---- shop tab
    def build_shop_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText(
            "Scan a barcode (6+ characters) or type a product ID, then press Enter")
        self.scan_input.returnPressed.connect(self.add_from_input)
        add = QPushButton("Add")
        add.clicked.connect(self.add_from_input)
        top.addWidget(self.scan_input)
        top.addWidget(add)
        lay.addLayout(top)

        self.cart_table = make_table(["Product", "Amount", "Price", "Best before"])
        self.cart_table.doubleClicked.connect(lambda _: self.edit_amount())
        lay.addWidget(self.cart_table)

        self.total_label = QLabel("Total: $0.00")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        self.total_label.setFont(f)
        self.total_label.setAlignment(Qt.AlignRight)
        lay.addWidget(self.total_label)

        row = QHBoxLayout()
        for label, fn in (("Edit amount", self.edit_amount), ("Remove item", self.remove_item),
                          ("Clear cart", self.clear_cart), ("Checkout", self.checkout)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        return w

    def pick_available(self, rows):
        in_cart = {i["code"] for i in self.cart}
        for r in rows:
            if r[TYPE] == "per kg" or r[CODE] not in in_cart:
                return r
        return None

    def add_from_input(self):
        text = self.scan_input.text().strip()
        self.scan_input.clear()
        if not text:
            return
        if len(text) > 5:
            row = self.stock.by_code(text)
        else:
            row = self.pick_available(self.stock.by_product_id(text.upper()))
        if row is None:
            self.statusBar().showMessage("Product not found (or all units are already in the cart).", 5000)
            return
        self.add_row_to_cart(row)
        self.scan_input.setFocus()

    def add_row_to_cart(self, row):
        code, name, ptype = row[CODE], row[NAME], row[TYPE]
        existing = next((i for i in self.cart if i["code"] == code), None)
        if ptype == "per kg":
            grams, ok = QInputDialog.getInt(
                self, "Amount", f"{name} - ${float(row[PRICE]):.2f} per kg\nAmount in grams:",
                500, 1, 1000000)
            if not ok:
                return
            if existing:
                existing["amount"] += grams
            else:
                self.cart.append({"code": code, "name": name, "amount": grams, "type": ptype,
                                  "unit_price": float(row[PRICE]), "bb": parse_date(row[BB])})
        else:
            if existing:
                self.statusBar().showMessage("That unit is already in the cart.", 5000)
                return
            self.cart.append({"code": code, "name": name, "amount": 1, "type": ptype,
                              "unit_price": float(row[PRICE]), "bb": parse_date(row[BB])})
        msg = f"Added {name} to the cart."
        bb, today = parse_date(row[BB]), date.today()
        if bb and today > bb:
            msg += " WARNING: product is expired!"
        elif bb and bb <= today + timedelta(days=7):
            msg += " Item will expire within a week."
        self.statusBar().showMessage(msg, 8000)
        self.refresh_cart()

    def refresh_cart(self):
        today, total, data, colors = date.today(), 0.0, [], []
        for it in self.cart:
            p = item_price(it)
            total += p
            amount = f"{it['amount']} g" if it["type"] == "per kg" else it["amount"]
            bb = it["bb"]
            colors.append(EXPIRED if bb and bb < today else
                          SOON if bb and bb <= today + timedelta(days=7) else None)
            data.append([it["name"], amount, f"${p:.2f}", bb.isoformat() if bb else "-"])
        fill_table(self.cart_table, ["Product", "Amount", "Price", "Best before"], data, colors)
        self.total_label.setText(f"Total: ${total:.2f}")

    def edit_amount(self):
        r = self.cart_table.currentRow()
        if r < 0:
            self.statusBar().showMessage("Select a cart item first.", 4000)
            return
        it = self.cart[r]
        if it["type"] != "per kg":
            QMessageBox.information(self, "Edit amount",
                                    "Only items sold by weight can be edited. "
                                    "Add another unit instead.")
            return
        grams, ok = QInputDialog.getInt(self, "Edit amount", f"{it['name']} - grams:",
                                        int(it["amount"]), 1, 1000000)
        if ok:
            it["amount"] = grams
            self.refresh_cart()

    def remove_item(self):
        r = self.cart_table.currentRow()
        if r >= 0:
            del self.cart[r]
            self.refresh_cart()

    def clear_cart(self):
        if self.cart and QMessageBox.question(self, "Clear cart", "Remove all items?") == QMessageBox.Yes:
            self.cart.clear()
            self.refresh_cart()

    def checkout(self):
        if not self.cart:
            self.statusBar().showMessage("The cart is empty.", 4000)
            return
        text = build_receipt(self.cart)
        dlg = ReceiptDialog(text, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        warnings = self.update_stock()
        if dlg.print_requested:
            print_text(text, self)
        if warnings:
            QMessageBox.warning(self, "Stock warning", "\n".join(warnings))
        self.cart.clear()
        self.refresh_cart()
        self.load_catalog()
        self.statusBar().showMessage("Sale completed - stock updated.", 6000)

    def update_stock(self):
        warnings = []
        for it in self.cart:
            if it["type"] == "per kg":
                row = self.stock.by_code(it["code"])
                kg_sold = it["amount"] / 1000
                if row is None or kg_sold > row[QTY]:
                    left = row[QTY] if row else 0
                    warnings.append(f"Not enough stock for {it['name']}: only {left} kg left, "
                                    f"tried to sell {kg_sold} kg. Stock not updated.")
                    continue
                self.stock.change_kg(it["code"], -kg_sold)
            else:
                self.stock.delete(it["code"])
        self.stock.commit()
        return warnings

    # ---- catalog tab
    def build_catalog_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        top.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(CATEGORIES)
        self.cat_combo.currentIndexChanged.connect(self.load_catalog)
        top.addWidget(self.cat_combo, 1)
        lay.addLayout(top)

        self.catalog_table = make_table(["Product", "Price", "In stock", "Best before"])
        lay.addWidget(self.catalog_table)

        row = QHBoxLayout()
        self.units_btn = QPushButton("View units")
        self.units_btn.clicked.connect(self.view_units)
        for label, fn in (("Add to cart", self.catalog_add_to_cart), ("Restock", self.restock)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addWidget(self.units_btn)
        lay.addLayout(row)
        return w

    def load_catalog(self):
        rows = self.stock.by_category(self.cat_combo.currentText())
        self.cat_type = rows[0][TYPE] if rows else None
        if self.cat_type == "per kg":
            headers = ["Product", "Price per kg", "Kg left", "Best before"]
            rows.sort(key=lambda r: str(r[NAME]).lower())
            self.catalog_groups = [[r] for r in rows]
            data = [[r[NAME], f"${float(r[PRICE]):.2f}", round(r[QTY], 1), r[BB]] for r in rows]
        else:
            headers = ["Product", "Price", "In stock", "Next best before"]
            groups = {}
            for r in rows:
                groups.setdefault(r[NAME], []).append(r)
            self.catalog_groups, data = [], []
            for name in sorted(groups, key=lambda n: str(n).lower()):
                g = sorted(groups[name], key=lambda r: str(r[BB]))
                self.catalog_groups.append(g)
                data.append([name, f"${float(g[0][PRICE]):.2f}", len(g), g[0][BB]])
        fill_table(self.catalog_table, headers, data)
        self.units_btn.setEnabled(self.cat_type == "per 1")

    def selected_group(self):
        r = self.catalog_table.currentRow()
        if r < 0 or r >= len(self.catalog_groups):
            self.statusBar().showMessage("Select an item first.", 4000)
            return None
        return self.catalog_groups[r]

    def catalog_add_to_cart(self):
        group = self.selected_group()
        if group:
            row = self.pick_available(group)
            if row is None:
                self.statusBar().showMessage("All units of this item are already in the cart.", 5000)
            else:
                self.add_row_to_cart(row)

    def view_units(self):
        group = self.selected_group()
        if group:
            UnitsDialog(group, self).exec_()

    def restock(self):
        group = self.selected_group()
        if not group:
            return
        first = group[0]
        if self.cat_type == "per kg":
            kg, ok = QInputDialog.getDouble(self, "Restock", f"Kg to add to {first[NAME]}:",
                                            1.0, 0.01, 100000, 2)
            if not ok:
                return
            self.stock.change_kg(first[CODE], kg)
        else:
            dlg = RestockDialog(first[NAME], self)
            if dlg.exec_() != QDialog.Accepted:
                return
            units, bb = dlg.values()
            try:
                codes = next_codes([g[CODE] for g in group], units)
            except ValueError as e:
                QMessageBox.warning(self, "Restock", str(e))
                return
            for code in codes:
                new = list(first)
                new[CODE], new[BB] = code, bb
                self.stock.insert(new)
        self.stock.commit()
        self.load_catalog()
        self.statusBar().showMessage(f"{first[NAME]} restocked.", 5000)

    def closeEvent(self, event):
        self.stock.conn.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    try:
        if not os.path.exists(DB_PATH):
            raise RuntimeError(f"Database '{DB_PATH}' not found in the current folder.")
        stock = StockDB(DB_PATH)
    except (RuntimeError, sqlite3.Error) as e:
        QMessageBox.critical(None, "SaPo Shop", str(e))
        return 1
    win = MainWindow(stock)
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())