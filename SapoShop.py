import datetime
import sqlite3
import os , platform
from datetime import date, timedelta
import time
cart = []
connection = sqlite3.connect("sapo_stockfinal.db")
c = connection.cursor()
d = date.today()

def cleener() :
    time.sleep(1.5)
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

print("=======================")
print("Welcome to SaPo Shop")
print("=======================")
print("Loading ")
time.sleep(1.5)
cleener()


while True:
    print ("choose action or scan a product")
    print("add product-1")
    print("print cart-2")
    print("catalog-3")
    menu_choice = input(":")
    cleener()

    if len(menu_choice) > 5:

        codechoice = menu_choice
        c.execute('SELECT * FROM stock WHERE code = ?', (codechoice,))
        product = c.fetchone()
        pname = product[1]

        if product[3] == str("per kg"):
            print("Found:", pname, "price per kg", "$" + str(product[2]))
            ammount = int(input("enter product amount in grams:"))
            pricepg = product[2] / 1000
            totalprice = pricepg * ammount
            fullproduct = product[0], pname, ammount, round(totalprice, 2), product[3]  # fixed: was product[7]
            cart.append(fullproduct)
            bbdate = date.fromisoformat(product[7])
            if d > bbdate:
                print("product is expired")
            elif bbdate <= d + timedelta(days=7):
                print("Item will expire within a week")
            print("added", pname, "to the cart")
            cleener()
        else:
            totalprice = product[2]
            ammount = 1
            fullproduct = product[0], pname, ammount, round(totalprice, 2), product[3]  # added type
            cart.append(fullproduct)
            print("added", pname, "$" + str(product[2]), "to the cart")
            cleener()

        time.sleep(1)

    if menu_choice == "1":
        codechoicecap = input("enter product id:").upper()
        codechoice = codechoicecap
        c.execute(
            'SELECT * FROM stock WHERE product_id = ? ORDER BY best_before_date ASC',
            (codechoice,)
        )
        product = c.fetchone()

        if product is None:
            print("product not found")
            continue

        pname = product[1]

        if product[3] == str("per kg"):
            print("Found:", pname, "price per kg", "$" + str(product[2]))
            ammount = int(input("enter product amount in grams:"))
            pricepg = product[2] / 1000
            totalprice = pricepg * ammount
            fullproduct = product[0], pname, ammount, round(totalprice, 2), product[3]  # product[0] = this row's code
            cart.append(fullproduct)
            bbdate = date.fromisoformat(product[7])
            if d > bbdate:
                print("product is expired")
            elif bbdate <= d + timedelta(days=7):
                print("Item will expire within a week")
            print("added", pname, "to the cart")
        else:
            totalprice = product[2]
            ammount = 1
            fullproduct = product[0], pname, ammount, round(totalprice, 2), product[3]
            cart.append(fullproduct)
            print("added", pname, "$" + str(product[2]), "to the cart")
        cleener()

    if menu_choice == "2":
        print("=======================")
        print ("Recipt")
        print("=======================")
        price = 0
        for item in cart:
            print("=======================")
            print("product:" + str(item[1]), "\namount:" + str(item[2]), "\nprice:$" + str(item[3]))
            price += float(item[3])
        print("=======================")
        print("your total price is $" + str(price))
        print("=======================")
        editchoice = input("to edit press 1 \nto print press 2 \n:")

        if editchoice == "2":
            def recipt():
                price = 0
                print("SaPo market")
                print(datetime.date.today())
                for item in cart:

                    print("=======================")
                    print("product:" + str(item[1]), "\namount:" + str(item[2]), "\nprice:$" + str(item[3]))
                    price += float(item[3])
                print("=======================")
                print("your total price is $" + str(price))

                for item in cart:
                    code = item[0]
                    item_type = item[4]

                    if item_type == "per kg":
                        c.execute('SELECT * FROM stock WHERE code = ?', (code,))
                        row = c.fetchone()
                        col_names = [d[0] for d in c.description]
                        quantity_col = col_names[5]

                        grams_sold = item[2]
                        kg_sold = grams_sold / 1000
                        kg_left = row[5]

                        if kg_sold > kg_left:
                            print(f"WARNING: not enough stock for {item[1]} — only {kg_left} kg left, "
                                  f"tried to sell {kg_sold} kg. Skipping stock update for this item.")
                            continue

                        c.execute(
                            f'UPDATE stock SET {quantity_col} = {quantity_col} - ? WHERE code = ?',
                            (kg_sold, code)
                        )
                    else:
                        c.execute('DELETE FROM stock WHERE code = ?', (code,))

                connection.commit()
                print("stock updated.")


            recipt()
        if editchoice == "1":
            for index, item in enumerate(cart):
                print(index + 1, item[1], "amount:", item[2], "price:", item[3])

            while True:
                editchoicenum = int(input("choose product to edit: ")) - 1
                amountchoice = float(input("choose amount: "))

                cart[editchoicenum] = list(cart[editchoicenum])
                old_amount = cart[editchoicenum][2]
                old_price = cart[editchoicenum][3]

                price_per_unit = old_price / old_amount
                new_price = amountchoice * price_per_unit

                cart[editchoicenum][2] = amountchoice
                cart[editchoicenum][3] = new_price

                print("item", cart[editchoicenum][1], "has been edited")

                continuechoice = input("next item? y/n ")
                if continuechoice == "y":
                    cleener()
                if continuechoice == "n":
                    cleener()
                    break

    if menu_choice == "3":
        print("=======================")
        print("catalog")
        print("=======================")
        categories = {
            "1": "vegetable",
            "2": "fruit",
            "3": "bakery",
            "4": "foodstuff",
            "5": "drinks",
            "6": "alcohol",
            "7": "sweets",
            "8": "misc",
            "9": "salty snacks",
        }

        for num, cat_name in categories.items():
            print(f"category {num} = {cat_name}")

        category_choice = input("choose category:")
        category_name = categories.get(category_choice)

        if category_name is None:
            print("Invalid category.")
            continue

        c.execute('SELECT * FROM stock WHERE category = ?', (category_name,))
        products = c.fetchall()

        if not products:
            print("No products found in this category.")
            continue

        category_type = products[0][3]

        if category_type == "per kg":
            for product in products:
                print(product[1], "-", "$" + str(product[2]), "per kg",
                      "-", round(product[5], 1), "kg left", "- best before:", product[7])

            action = input("press 'a' to add stock, or Enter to go back: ").strip().lower()
            if action == "a":
                target_name = input("enter product name to restock: ").strip()
                matches = [p for p in products if p[1].lower() == target_name.lower()]
                if not matches:
                    print("Item not found in this category.")
                    continue

                row = matches[0]
                code = row[0]
                kg_to_add = float(input(f"enter kg to add to {row[1]}: "))

                c.execute('SELECT * FROM stock WHERE code = ?', (code,))
                col_names = [d[0] for d in c.description]
                quantity_col = col_names[5]

                c.execute(
                    f'UPDATE stock SET {quantity_col} = {quantity_col} + ? WHERE code = ?',
                    (kg_to_add, code)
                )
                connection.commit()
                print(f"added {kg_to_add} kg to {row[1]}. stock updated.")

        elif category_type == "per 1":
            distinct_names = sorted(set(p[1] for p in products))
            for i, name in enumerate(distinct_names, start=1):
                print(i, "-", name)

            item_choice = input("choose item (number or name), or 'a' to add stock:").strip()

            if item_choice.lower() == "a":
                target_name = input("enter product name to restock: ").strip()
                matches = [p for p in products if p[1].lower() == target_name.lower()]
                if not matches:
                    print("Item not found in this category.")
                    continue

                template = matches[0]
                col_names = [d[0] for d in c.description]

                existing_codes = [m[0] for m in matches]
                suffixes = []
                for ec in existing_codes:
                    prefix, suffix = ec.rsplit("I", 1)
                    suffixes.append((prefix, suffix, int(suffix)))
                code_prefix = suffixes[0][0]
                suffix_width = len(suffixes[0][1])
                highest_num = max(s[2] for s in suffixes)

                units_to_add = int(input(f"how many units of {template[1]} to add: "))
                new_bbdate = input("enter best-before date for this batch (YYYY-MM-DD): ").strip()

                for i in range(1, units_to_add + 1):
                    new_num = highest_num + i
                    new_code = code_prefix + "I" + str(new_num).zfill(suffix_width)

                    new_row = list(template)
                    new_row[0] = new_code
                    new_row[7] = new_bbdate

                    placeholders = ", ".join("?" for _ in col_names)
                    columns = ", ".join(col_names)
                    c.execute(f'INSERT INTO stock ({columns}) VALUES ({placeholders})', new_row)

                connection.commit()
                print(f"added {units_to_add} unit(s) of {template[1]} to stock.")
                continue

            if item_choice.isdigit() and 1 <= int(item_choice) <= len(distinct_names):
                chosen_name = distinct_names[int(item_choice) - 1]
            else:
                chosen_name = item_choice

            matches = [p for p in products if p[1].lower() == chosen_name.lower()]

            if not matches:
                print("Item not found in this category.")
                continue

            for m in matches:
                print(m[0], "-", "$" + str(m[2]), "- best before:", m[7])
