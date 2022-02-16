from flask import Flask, render_template, flash, url_for, redirect, request, send_file, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField,IntegerField, PasswordField, BooleanField, SelectField, DateField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, InputRequired 
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
import requests
from numpy import cumsum, array
import uuid
import datetime as dt
from sqlalchemy.sql import extract
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import gspread
import string
from cryptography.fernet import Fernet
from num2words import num2words as n2w
from wtforms_sqlalchemy.fields import QuerySelectField
#from flask_migrate import Migrate
from sqlalchemy import or_, and_, func
import sqlite3
import pandas as pd
import os
from helpers import generate_student_id, generate_receipt_no, promote_student, date_transform, inside, encrypt_text, decrypt_text
from forms import (ClientSignUpForm, ClientLogInForm, ToDoForm, StudentPaymentsForm, ExpensesForm, PTAExpensesForm, ETLExpensesForm, ReportsForm, ChargeForm, SearchForm, StudentLedgerForm)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///client.db'
app.config['SQLALCHEMY_BINDS'] = {"kpasec": "sqlite:///kpasec.db", "kpasecarchives":"sqlite:///kpasecarchives.db"}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = "87ys!7278127anjahash"#os.environ.get('KPASEC_APP')
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
#migrate = Migrate(app, db)

#key = Fernet.generate_key()
#fernet = Fernet(key)
#google_sheeet = gspread.service_account(filename="kpasec.json")
#main_sheet = google_sheeet.open("KpasecSystem")
#student_sheet = main_sheet.worksheet("StudentInfo")




@app.template_filter()
def currencyFormat(value):
	value = float(value)
	if value >= 0:
		return "{:,.2f}".format(value)
	else:
		value2 = "{:,.2f}".format(value)
		return "("+value2[1:]+")"


@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))

@app.route("/")
def home():
    return render_template("homepage1.html")


@app.route("/register_user", methods = ['GET', 'POST'])
def register_user():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = UserSignUpForm()
	if form.validate_on_submit():
		print('validate')
		if request.method == "POST":
			username = form.data.get('username')
			email = form.data.get('email')
			password = form.data.get('password')
			function = form.data.get('function')
			hash_password = bcrypt.generate_password_hash(password).decode("utf-8")
			data = User(username=username, email=email, password=hash_password, function=function)
			db.session.add(data)
			db.session.commit()
		flash(f"Account successfully created for {form.username.data}", "success")
		return redirect(url_for("login"))
	return render_template("user_register.html", form=form)



@app.route("/login", methods = ['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = UserLogInForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user and bcrypt.check_password_hash(user.password, form.password.data):
			login_user(user, remember=form.remember.data)
			next_page = request.args.get('next')
			return redirect(next_page) if next_page else redirect(url_for('account'))
		else:
			flash("Login unsuccessful, please try again", "danger")
	return render_template("user_login1.html", form=form)



@app.route("/logout")
def logout():
	logout_user()
	return redirect(url_for("login"))


@app.route("/accountant_dashboard/pta_expenses", methods = ['GET', 'POST'])
@login_required
def pta_expenses():
	if current_user.is_authenticated  and current_user.approval:
		title = "Make PTA Expense"
		form = PTAExpensesForm()
		if form.validate_on_submit():
			purchase_date = form.data.get('purchase_date')
			item = form.data.get('item')
			purpose = form.data.get('purpose')
			totalcost = form.data.get('totalcost')
			quantity = form.data.get('quantity')
			unitcost = form.data.get('unitcost')
			semester = current_sem
			exp1 = Expenses(date = purchase_date, item=item, purchase_date=purchase_date, purpose=purpose, quantity=quantity,
				unitcost=unitcost, totalcost=totalcost, semester=semester)
			pta1 = PTAExpenses(item=item, purchase_date=purchase_date, purpose=purpose, quantity=quantity, unitcost=unitcost, 
				totalcost=totalcost, semester=semester)
			balance = int(obtain_cash_book_balances(CashBook))
			balance1 = int(obtain_cash_book_balances(PTACashBook))
			db.session.add(exp1)
			db.session.add(pta1)
			db.session.commit()
			idx1 = Expenses.query.all()[-1].id
			idx2 = PTAExpenses.query.all()[-1].id
			cash = CashBook(date=purchase_date,amount=totalcost, category="payment", semester=semester, 
				balance=str(balance), expense_id=idx1, details = item)
			ptacash = PTACashBook(details='PTA Expense', amount=totalcost, category="payment", semester=semester, 
				balance = balance1, expense_id=idx2)
			db.session.add(cash)
			db.session.add(ptacash)
			db.session.commit()
			flash("Data successfully saved", "success")
			return redirect(url_for("gen_expenses"))
		return render_template("pta_expenses_form.html", form=form, title=title)
	else:
		abort(404)


@app.route("/accountant_dashboard/etl_expenses", methods = ['GET', 'POST'])
@login_required
def etl_expenses():
	if current_user.is_authenticated  and current_user.approval:
		title = "Make ETL Expense"
		form = ETLExpensesForm()
		if form.validate_on_submit():
			purchase_date = form.data.get('purchase_date')
			item = form.data.get('item')
			purpose = form.data.get('purpose')
			totalcost = form.data.get('totalcost')
			quantity = form.data.get('quantity')
			unitcost = form.data.get('unitcost')
			
			semester = current_sem

			
			balance = int(obtain_cash_book_balances(CashBook))
			balance1 = int(obtain_cash_book_balances(ETLCashBook))

			exp1 = Expenses(date = purchase_date, item=item, purchase_date=purchase_date, purpose=purpose, quantity=quantity,
				unitcost=unitcost, totalcost=totalcost, semester=semester)
			etl1 = ETLExpenses(item=item, purchase_date=purchase_date, purpose=purpose, quantity=quantity, unitcost=unitcost, 
				totalcost=totalcost, semester=semester)
			db.session.add(exp1)
			db.session.add(etl1)
			db.session.commit()
			idx1 = Expenses.query.all()[-1].id
			idx2 = ETLExpenses.query.all()[-1].id
			cash = CashBook(date=purchase_date,amount=totalcost, category="payment", semester=semester, 
				balance=str(balance), expense_id=idx1+1, details = item)
			etlcash = ETLCashBook(details='ETL Expense',date=purchase_date,amount=totalcost, category="payment", semester=semester, 
				balance = balance1, expense_id=idx2+1)
			
			
			db.session.add(cash)
			db.session.add(etlcash)
			db.session.commit()
			flash("Data successfully saved", "success")
			return redirect(url_for("gen_expenses"))
		return render_template("etl_expenses_form.html", form=form, title=title)
	else:
		abort(404)


@app.route("/account")
@login_required
def account():
	return render_template("account.html")


@app.route("/accountant_dashboard/promote_all_students")
@login_required
def promote_all_students():
	students = Student.query.all()
	for stud in students:
		new_class = promote_student(stud.class1)
		if new_class:
			stud.class1 = new_class
		else:
			pass
	db.session.commit()
	return "All students promoted!"


@app.route("/accountant_dashboard/semester/charges")
@login_required
def charges():
	if current_user.is_authenticated and current_user.approval:
		form = ChargeForm()
		if form.validate_on_submit():
			etl = form.data.get('etl')
			pta = form.data.get('pta')
			begin = form.data.get('begin_date')
			end = form.data.get('end_date')
			sem = form.data.get('semester')
			total = etl + pta
			charge = Charges(begin_date=begin, end_date=end, etl=etl, pta=pta,
			 total=total, semester=sem)
			
			db.session.add(charge)
			db.session.add(pmt)
			db.session.commit()
		return render_template("charges.html", form=form)
	else:
		abort(404)


@app.route("/clerk_dashboard", methods=['GET', 'POST'])
@login_required
def clerk_dashboard():
	if current_user.is_authenticated and current_user.approval:
		form1 = SearchForm()
		form2 = StudentSignUp()

		if form2.data['register_submit'] and form2.validate_on_submit():
			name = form2.data.get("name")
			class1 = form2.data.get("class1")
			dob = form2.data.get("date_of_birth")
			date_ad = form2.data.get("date_admitted")
			phone = form2.data.get("parent_contact")
			phone1 = form2.data.get("phone")
			idx = generate_student_id(phone, dob)
			stud = Student(date=date_ad,fullname=name, phone=phone1, date_of_birth=dob, class1=class1.class1, parent_contact=phone, id_number=idx, date_admitted=date_ad)
			db.session.add(stud)
			db.session.commit()
			flash(f"{name} successfully registered!", "success")
			return redirect(url_for('clerk_dashboard'))


		if form1.data['search_submit'] and form1.validate_on_submit():
			phone = form1.data.get('parent_contact')
			dob = form1.data.get('date_of_birth')
			stud_id = generate_student_id(contact=phone, dob=dob)
			student = Student.query.filter_by(id_number=stud_id).first()
			if student:
				name = encrypt_text(student.fullname)
				dob = student.date_of_birth
				phone = encrypt_text(student.parent_contact)
				idx = student.id
				return redirect(url_for('pay_search_result', name=name, dob=dob, phone=phone, idx=idx, class1=student.class1))
			else:
				flash("No record found, please check and try again!", "danger")
		today = datetime.utcnow()
		date = dt.date(today.year, today.month, today.day)
		payments = StudentPayments.query.filter(func.date(StudentPayments.date) == date).all()
		etl = sum([pmt.etl_amount for pmt in payments if pmt.category != 'charge'])
		pta = sum([pmt.pta_amount for pmt in payments if pmt.category != 'charge'])

		student = len(set([pmt.payer.id_number for pmt in payments if pmt.payer is not None]))

		expenses = Expenses.query.filter(func.date(Expenses.date) == date).all()
		expense = sum([exp.totalcost for exp in Expenses.query.all()])
		total = etl + pta
		return render_template('clerk_dashboard.html', form1=form1, form2=form2, expense=expense, 
			etl=etl, pta=pta, total=total, student=student)
	else:
		abort(404)



@app.route("/accountant_dashboard/all_students")
@login_required
def all_students():
	if current_user.is_authenticated and current_user.approval:
		students = Student.query.all()
		return render_template("all_students.html", students=students)
	else:
		abort(404)

@app.route("/accountant_dashboard/cash_book_report/<string:start1>, <string:end1>, <category>")
@login_required
def cash_book_report(start1, end1, category):
	if current_user.is_authenticated  and current_user.approval:
		start, end = date_transform(start1,end1)
		category = decrypt_text(encrypted_text=category)
		if category == "PTA Levy":
			cash_book = PTACashBook.query.filter(PTACashBook.date.between(start, end)).all()
			income = [i.amount for i in cash_book if i.category == "revenue"]
			expense = [i.amount for i in cash_book if i.category == "payment"]
			balance, bf, bfdate = bal_date(cash_book, book=PTACashBook)
		if category == "ETL":
			cash_book = ETLCashBook.query.filter(ETLCashBook.date.between(start, end)).all()
			income = [i.amount for i in cash_book if i.category == "revenue"]
			expense = [i.amount for i in cash_book if i.category == "payment"]
			balance, bf, bfdate = bal_date(cash_book, book=ETLCashBook)
		if category == "ETL & PTA Levy":
			cash_book = CashBook.query.filter(CashBook.date.between(start, end)).all()
			income = [i.amount for i in cash_book if i.category == "revenue"]
			expense = [i.amount for i in cash_book if i.category == "payment"]
			balance, bf, bfdate = bal_date(cash_book, book=CashBook)
		
		return render_template("cash_book.html", cash_book=cash_book, balance=balance, 
			debit=sum(income), credit = sum(expense), bal1 = sum(income)-sum(expense), 
			category=category, start=start, end=end1, bf=bf, bfdate=bfdate)
	else:
		abort(404)

def bal_date(cash_book, book):
	if len(cash_book) >= 1:
		cash_bk = cash_book[0].id
		bf1 = book.query.get_or_404(cash_bk)
		bf = bf1.balance
		bfdate = bf1.date.date()
	else:
		bf = 0
		bfdate = None
	balance = [bf] + [i.amount if i.category =="revenue" else -1*i.amount for i in cash_book]
	balance = cumsum(balance)
	return balance, bf, bfdate


@app.route("/accountant_dashboard/expenses_statement/<start1>, <end1>, <category>")
@login_required
def expenses_statement(start1, end1, category):
	if current_user.is_authenticated and current_user.approval:
		if category == 'ETL & PTA Levy':
			start, end = date_transform(start1,end1)
			expenses = Expenses.query.filter(Expenses.date.between(start, end)).all()
			cum1 = cumsum([exp.totalcost for exp in expenses ])
			if len(cum1) < 1:
				flash(f"No data for the period {start} to {end1}", "success")
				return redirect(url_for('accountant_dashboard'))
			return render_template("expenses_statement.html", expenses=expenses, cum1=cum1, start=start, end=end1)
		if category == 'ETL':
			return redirect(url_for('etl_expenses_statement', start1=start1, end1=end1))
		if category == 'PTA Levy':
			return redirect(url_for('pta_expenses_statement', start1=start1, end1=end1))
	abort(404)


@app.route("/accountant_dashboard/pta_expenses_statement/<start1>, <end1>")
@login_required
def pta_expenses_statement(start1, end1):
	if current_user.is_authenticated and current_user.approval:
		start, end = date_transform(start1,end1)
		expenses = PTAExpenses.query.filter(PTAExpenses.date.between(start, end)).all()
		cum1 = cumsum([exp.totalcost for exp in expenses ])
		if len(cum1) < 1:
			flash(f"No data for the period {start} to {end1}", "success")
			return redirect(url_for('accountant_dashboard'))
		return render_template("pta_expenses_statement.html", expenses=expenses, cum1=cum1, start=start, end=end1)
	abort(404)


@app.route("/accountant_dashboard/etl_expenses_statement/<start1>, <end1>")
@login_required
def etl_expenses_statement(start1, end1):
	if current_user.is_authenticated and current_user.approval:
		start, end = date_transform(start1,end1)
		expenses = ETLExpenses.query.filter(ETLExpenses.date.between(start, end)).all()
		cum1 = cumsum([exp.totalcost for exp in expenses ])
		if len(cum1) < 1:
			flash(f"No data for the period {start} to {end1}", "success")
			return redirect(url_for('accountant_dashboard'))
		return render_template("etl_expenses_statement.html", expenses=expenses, cum1=cum1, start=start, end=end1)
	abort(404)


@app.route("/accountant_dashboard/income_statement/<start1>, <end1>, <category>")
@login_required
def income_statement(start1, end1, category):
	if current_user.is_authenticated and current_user.approval:
		start, end = date_transform(start1,end1)
		if category == "PTA Levy":
			incomes = PTAIncome.query.filter(PTAIncome.date.between(start, end)).filter(PTAIncome.category=='revenue').all()	
		if category == "ETL":
			incomes = ETLIncome.query.filter(ETLIncome.date.between(start, end)).filter(ETLIncome.category=='revenue').all()
		if category == "ETL & PTA Levy":
			incomes = StudentPayments.query.filter(StudentPayments.date.between(start, end)).filter(StudentPayments.category=='revenue').all()
		cum1 = cumsum([inc.amount for inc in incomes if inc.category != 'charge'])
		if len(incomes) < 1:
			flash(f"No data for the period {start} to {end1}", "success")
			return redirect(url_for('accountant_dashboard'))
		return render_template("income_statement.html", incomes=incomes, start=start, end=end1,category=category, cum1=cum1)
	else:
		abort(404)


@app.route("/accountant_dashboard/income_and_expenditure/<start1>, <end1>, <category>")
@login_required
def income_and_expenditure(start1, end1, category):
	if current_user.is_authenticated and current_user.approval:
		start, end = date_transform(start1,end1)
		if category == "PTA Levy":
			incomes = PTAIncome.query.filter(PTAIncome.date.between(start, end)).filter(PTAIncome.category=='revenue').all()
			expenses = PTAExpenses.query.filter(PTAExpenses.date.between(start, end)).all()	
		if category == "ETL":
			incomes = ETLIncome.query.filter(ETLIncome.date.between(start, end)).filter(ETLIncome.category=='revenue').all()
			expenses = ETLExpenses.query.filter(ETLExpenses.date.between(start, end)).all()
		if category == "ETL & PTA Levy":
			incomes = StudentPayments.query.filter(StudentPayments.date.between(start, end)).filter(StudentPayments.category=='revenue').all()
			expenses = Expenses.query.filter(Expenses.date.between(start, end)).all()
		c1 = [inc.amount for inc in incomes if inc.category != 'charge' ] 
		c2 = [-1*exp.totalcost for exp in expenses ]
		cums = cumsum(c1+c2)
		return render_template("income_expend.html", incomes=incomes, expenses=expenses, cums=cums, 
			sum1 = sum(c1), sum2=-1*sum(c2), category=category, start=start, end=end1)
	else:
		abort(404)


@app.route("/accountant_dashboard/begin_sem", methods=['GET', 'POST'])
@login_required
def begin_sem():
	if current_user.is_authenticated and current_user.approval:
		form = ChargeForm()
		if form.validate_on_submit():
			etl = form.data.get('etl')
			pta = form.data.get('pta')
			begin = form.data.get('begin_date')
			end = form.data.get('end_date')
			sem = form.data.get('semester')
			total = etl + pta
			charge = Charges(begin_date=begin, end_date=end, etl=etl, pta=pta,
			 total=total, semester=sem)
			etl_data = ETLIncome(date = begin, amount=etl, tx_id=None, semester=sem, mode_of_payment=None, student_id=None, category='charge')
			pta_data = PTAIncome(date = begin, amount=pta, tx_id=None, semester=sem, mode_of_payment=None, student_id=None, category='charge')
			pmt = StudentPayments(date = begin, etl_amount=etl, pta_amount=pta, amount=total, category="charge", semester=sem)
			db.session.add(charge)
			db.session.add(pmt)
			db.session.add(etl_data)
			db.session.add(pta_data)
			db.session.commit()
			flash("Successfully saved semester charges!", "success")
			return redirect(url_for("begin_sem"))
		return render_template("begin_sem.html", form=form)
	else:
		abort(404)


@app.route("/accountant_dashboard", methods=['POST', 'GET'])
@login_required
def accountant_dashboard():
	if current_user.is_authenticated and current_user.approval:
		studs = len(Student.query.all())
		incomes = StudentPayments.query.all()
		etl = sum([inc.etl_amount for inc in incomes if inc.category == 'revenue'])
		pta = sum([inc.pta_amount for inc in incomes if inc.category == 'revenue'])
		form1 = ExpensesForm()
		form2 = ReportsForm()
		if form2.data['submit_rep'] and form2.validate_on_submit():
			report = form2.data.get("report")
			filter_by = form2.data.get("filter_by")
			start = form2.data.get("start")
			end = form2.data.get("end")
			if report == "Cash Book":
				category = encrypt_text(plain_text=filter_by)
				return redirect(url_for('cash_book_report', start1=start, end1=end, category=category))
			if report == "Income Statement":
				return redirect(url_for('income_statement', start1=start, end1=end, category=filter_by))
			if report == "Expenditure Statement":
				return redirect(url_for('expenses_statement', start1=start, end1=end, category=filter_by))
			if report == "Income & Expenditure":
				return redirect(url_for('income_and_expenditure', start1=start, end1=end, category=filter_by))
		expense = sum([exp1.totalcost for exp1 in Expenses.query.all()])
		todo = ToDoForm()
		if todo.data['submit_do'] and todo.validate_on_submit():
			if todo.data.get('task') == "Make ETL Expenses":
				return redirect(url_for('etl_expenses'))
			if todo.data.get('task') == "Make PTA Expenses":
				return redirect(url_for('pta_expenses'))
			if todo.data.get('task') == "Begin Semester":
				return redirect(url_for('begin_sem'))

		return render_template("accountant_dashboard.html", todo=todo, form1=form1, studs=studs, income=pta+etl, pta=pta, etl=etl,
			expense=expense, form2=form2)
	else:
		abort(404)


@app.route("/accountant_dashboard/student_classes/", methods=['POST', 'GET'])
@login_required
def student_classes():
	if current_user.is_authenticated and current_user.approval:
		newclass = NewClassForm()
		if newclass.validate_on_submit():
			cls1 = Classes(class1=newclass.data.get('newclass'))
			db.session.add(cls1)
			db.session.commit()
			flash(f"Class {newclass.data.get('newclass')} added class lists", "success")
		classes = Classes.query.all()
		
		return render_template("students_classes.html", newclass=newclass, classes=classes)
	else:
		abort(404)

@app.route("/accountant_dashboard/search_ledgers", methods=['POST','GET'])
@login_required
def search_ledgers():
	if current_user.is_authenticated and current_user.approval:
		form = StudentLedgerForm()
		if form.validate_on_submit():
			phone = form.data.get("phone")
			dob = form.data.get("dob")
			dob1 = dt.date(day=dob.day, month=dob.month, year=dob.year)
			phone = encrypt_text(str(phone))
			return redirect(url_for('ledger_results', phone=phone, dob=dob1))
		return render_template("search_ledger.html", form=form)
	else:
		abort(404)


@app.route("/clerk_dashboard/student/pay_search_result/<name>,<dob>,<phone>, <int:idx>, <class1>", methods=['GET', 'POST'])
@login_required
def pay_search_result(name, dob, phone, idx, class1):
	if current_user.is_authenticated and current_user.approval:
		form = StudentPaymentsForm()
		token = form.csrf_token
		name = decrypt_text(name)
		dob = dob
		phone = decrypt_text(phone)
		idx = idx
		if request.method == 'POST':
			pta = request.form.get('pta')
			etl = request.form.get('etl')
			pta1 = request.form.get('pta1')
			etl1 = request.form.get('etl1')
			semester = request.form.get('semester')
			mode = 'cash'

			tx_id = generate_receipt_no()
			balance = int(obtain_cash_book_balances(CashBook))
			balance1 = int(obtain_cash_book_balances(ETLCashBook))
			balance2 = int(obtain_cash_book_balances(PTACashBook))

			if etl and not pta:
				amount = int(etl)
				pta = 0
				pmt_data = StudentPayments(etl_amount=etl, pta_amount=0, semester=semester, mode_of_payment=mode, student_id=idx, amount=amount, tx_id=tx_id)
				etl_data = ETLIncome(amount=etl, tx_id=tx_id, semester=semester, mode_of_payment=mode, student_id=idx)
				id2 = ETLIncome.query.all()[-1].id
				id1 = StudentPayments.query.all()[-1].id
				etlcash = ETLCashBook(amount=etl, category="revenue", semester=semester, balance = balance1, income_id=id2+1)
				cash = CashBook(etl=etl, pta=0, category='revenue', semester=semester, balance=balance, income_id=id1+1, amount=amount)
				db.session.add(etl_data)
				db.session.add(pmt_data)
				db.session.add(cash)
				db.session.add(etlcash)

			if pta and not etl:
				amount = int(pta)
				etl = 0
				pmt_data = StudentPayments(etl_amount=0, pta_amount=pta, semester=semester, mode_of_payment=mode, student_id=idx, amount=amount, tx_id=tx_id)
				pta_data = PTAIncome(amount=pta, tx_id=tx_id, semester=semester, mode_of_payment=mode, student_id=idx)
				id1 = StudentPayments.query.all()[-1].id
				id2 = PTAIncome.query.all()[-1].id
				ptacash = PTACashBook(amount=pta, category="revenue", semester=semester, balance = balance2, income_id=id2+1)
				cash = CashBook(etl=0, pta=pta, category='revenue', semester=semester, balance=balance, income_id=id1+1, amount=amount)	
				db.session.add(pta_data)
				db.session.add(pmt_data)
				db.session.add(cash)
				db.session.add(ptacash)

			if pta and etl:
				amount = int(pta) + int(etl)
				pmt_data = StudentPayments(etl_amount=etl, pta_amount=pta, semester=semester, mode_of_payment=mode, student_id=idx, amount=amount, tx_id=tx_id)
				pta_data = PTAIncome(amount=pta, tx_id=tx_id, semester=semester, mode_of_payment=mode, student_id=idx)
				etl_data = ETLIncome(amount=etl, tx_id=tx_id, semester=semester, mode_of_payment=mode, student_id=idx)
				id1 = StudentPayments.query.all()[-1].id
				id2 = PTAIncome.query.all()[-1].id
				id3 = ETLIncome.query.all()[-1].id
				ptacash = PTACashBook(amount=pta, category="revenue", semester=semester, balance = balance2, income_id=id2+1)
				etlcash = ETLCashBook(amount=etl, category="revenue", semester=semester, balance = balance1, income_id=id3+1)
				cash = CashBook(etl=etl, pta=pta, category='revenue', semester=semester, balance=balance, income_id=id1+1, amount=amount)	
				db.session.add(pta_data)
				db.session.add(etl_data)
				db.session.add(pmt_data)
				db.session.add(cash)
				db.session.add(ptacash)
				db.session.add(etlcash)

			student = Student.query.get_or_404(idx)
			name = student.fullname
			contact = student.parent_contact
			class1 = student.class1
		
			db.session.commit()

			tx_id = encrypt_text(str(tx_id))
			name = encrypt_text(name)
			contact = encrypt_text(contact)

			flash(f"Payment successfully made!", "success")
			return redirect(url_for('receipt', num=tx_id, name=name, etl_amount=etl, pta_amount=pta, contact=contact, class1=class1))
				
		return render_template("pay_search_results.html", class1=class1, fullname=name, date_of_birth=dob, 
			parent_contact=phone, token=token)
	else:
		abort(404)


@app.route("/clerk_dashboard/receipt/<num>, <name>, <etl_amount>, <pta_amount>, <contact>, <class1>")
@login_required
def receipt(num, name, etl_amount, pta_amount, contact, class1):
	if current_user.is_authenticated and current_user.approval:
		num = decrypt_text(num)
		name = decrypt_text(name)
		contact = decrypt_text(contact)
		today = dt.datetime.now()
		etl_words = n2w(int(etl_amount))
		pta_words = n2w(int(pta_amount))
		total = int(etl_amount) + int(pta_amount)
		return render_template("receipt.html",day=today.day, month=today.month, year=today.year, 
			num=num, name=name, etl_amount=etl_amount, pta_amount=pta_amount, 
			etl_words=etl_words.upper(), pta_words=pta_words.upper(), total=total, 
			contact=contact, class1=class1)
	else:
		abort(404)

@app.route("/accountant_dashboard/expenses/gen_expenses")
@login_required
def gen_expenses():
	if current_user.is_authenticated and current_user.approval:
		expenses = Expenses.query.all()
		total = sum([exp.totalcost for exp in expenses])
		return render_template("gen_expenses.html", expenses=expenses, total=total)
	else:
		abort(404)

@app.route("/accountant_dashboard/total_etl_income")
@login_required
def total_etl_income():
	if current_user.is_authenticated and current_user.approval:
		incomes = ETLIncome.query.all()
		return render_template("total_etl_income.html", incomes=incomes)
	else:
		abort(404)

@app.route("/accountant_dashboard/total_pta_income")
@login_required
def total_pta_income():
	if current_user.is_authenticated and current_user.approval:
		incomes = PTAIncome.query.all()
		return render_template("total_pta_income.html", incomes=incomes)
	else:
		abort(404)

@app.route("/clerk_dashboard/clerk_daily_report")
@login_required
def clerk_daily_report():
	if current_user.is_authenticated and current_user.approval:
		today = datetime.utcnow()
		date = dt.date(today.year, today.month, today.day)
		payments = StudentPayments.query.filter(func.date(StudentPayments.date) == date).all()
		etl = sum([pmt.etl_amount for pmt in payments if pmt.category != 'charge'])
		pta = sum([pmt.pta_amount for pmt in payments if pmt.category != 'charge'])
		return render_template("clerk_daily_report.html", payments=payments, etl=etl, pta=pta, date=date)
	else:
		abort(404)

@app.route("/accountant_dashboard/search_ledgers/ledger_results/<string:phone>, <string:dob>")
@login_required
def ledger_results(phone, dob):
	if current_user.is_authenticated and current_user.approval:
		phone1 = '0' + decrypt_text(phone)
		idx = generate_student_id(phone1, dob)
		student = Student.query.filter_by(id_number=idx).first()
		if student:
			charge = Charges.query.filter(Charges.begin_date >= student.date_admitted).all()
			payments = db.session.query(StudentPayments).filter(and_(or_(StudentPayments.student_id==student.id,StudentPayments.category=='charge'), StudentPayments.date >= student.date)).all()
			pmt2 = StudentPayments.query.filter_by(student_id=student.id)
			etls = db.session.query(ETLIncome).filter(and_(or_(ETLIncome.student_id==student.id, ETLIncome.category=='charge'), ETLIncome.date >= student.date)).all()
			ptas = db.session.query(PTAIncome).filter(and_(or_(PTAIncome.student_id==student.id, PTAIncome.category=='charge'), PTAIncome.date >= student.date)).all()
			pta = [i.amount if i.category =="revenue" else -1*i.amount for i in ptas]
			etl = [i.amount if i.category =="revenue" else -1*i.amount for i in etls]
			total = sum(etl) + sum(pta)
			cum1 = cumsum(etl)
			cum2 = cumsum(pta)
			if len(charge) > 0:
				charge = charge[-1]
			else:
				charge = 0
			return render_template("ledger_results1.html", student=student, payments=payments, cum1=cum1, cum2=cum2,
			 charge=charge, etls=etls, ptas=ptas)
		else:
			flash("Student not found!", "danger")
			return redirect(url_for('search_ledgers'))
	else:
		abort(404)



@app.route("/accountant_dashboard/delete_class/<int:id>", methods=['GET'])
@login_required
def delete_class(id):
    cls1 = Classes.query.get_or_404(id)
    db.session.delete(cls1)
    db.session.commit()
    flash(f'The class {cls1.class1} has been deleted!', 'success')
    return redirect(url_for('student_classes'))






class Classes(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	class1 = db.Column(db.String(10), unique=False, nullable=False)

	def __repr__(self):
		return f'User: {self.class1}'





#FORMS
def classquery():
	return Classes.query


class StudentSignUp(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired()])
    date_of_birth = DateField("Date of Birth", validators=[DataRequired()])
    date_admitted = DateField("Date of Admission", validators=[DataRequired()])
    class1 = QuerySelectField(query_factory=classquery, get_label = 'class1', allow_blank = True)
    parent_contact = StringField("Parent Contact", validators=[DataRequired(), Length(min=10, max=13)])
    phone = StringField("Student Phone #", validators = [Length(min=10, max=13)])
    register_submit = SubmitField("Register")

    def validate_date_admitted(self, date_admitted):
    	today = datetime.utcnow()
    	today = dt.date(year=today.year, month=today.month, day=today.day)
    	date_admitted1 = dt.date(year=date_admitted.data.year, month=date_admitted.data.month, day=date_admitted.data.day)
    	if date_admitted1 > today:
    		raise ValidationError(f"Date cant't be further than {today}")

class UserSignUpForm(FlaskForm):
    username = StringField("Full Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=20)])
    confirm_password = PasswordField("Comfirm Password", validators = [DataRequired(), EqualTo('password')])
    function = SelectField("Role", choices = ['','account', 'clerk'], validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self, email):
    	user = User.query.filter_by(email=email.data).first()
    	if user:
    		raise ValueError("The email is already in use, please choose a different one")


class UserLogInForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")

    def validate_password2022(self, password):
    	characters = ['=', '.','<','>', '-', '_', '/', '?', '!']
    	for char in characters:
    		if char in password.data:
    			raise ValidationError(f"{char} are not acceppted")



class NewClassForm(FlaskForm):
	newclass = StringField("Class Name", validators=[DataRequired(), Length(max	= 5)])
	submit = SubmitField("create")

	def validate_newclass(self, newclass):
		cls1 = Classes.query.filter_by(class1=newclass.data).first()
		if cls1:
			raise ValidationError("Class already exist!")




#DATABASES
class Client(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default = datetime.utcnow())
    company_name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'User: {self.company_name}'



class User(db.Model, UserMixin):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	username = db.Column(db.String(80), unique=False, nullable=False)
	email = db.Column(db.String(120), unique=True, nullable=False)
	password = db.Column(db.String(120), nullable=False)
	is_admin = db.Column(db.Boolean,  default=False)
	function = db.Column(db.String(120))
	approval = db.Column(db.Boolean, default=False)
	

	def __repr__(self):
		return f'User: {self.username}'




class Student(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	date_admitted = db.Column(db.DateTime)
	fullname = db.Column(db.String(80), unique=False, nullable=False)
	date_of_birth = db.Column(db.String(10), unique=True)
	class1 = db.Column(db.String(10), unique=False, nullable=False)
	parent_contact = db.Column(db.String(12), nullable=False)
	phone = db.Column(db.String(12))
	id_number = db.Column(db.String(120), unique=True, nullable=False)
	status = db.Column(db.Boolean, default=True)
	pta = db.relationship('PTAIncome', backref='pta_payer', lazy=True)#Here we reference the class
	etl = db.relationship('ETLIncome', backref='etl_payer', lazy=True)
	payer = db.relationship('StudentPayments', backref='payer', lazy=True)

	def __repr__(self):
		return f'User: {self.fullname}'


class PTAIncome(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	amount = db.Column(db.Integer)
	tx_id = db.Column(db.String(16))
	semester = db.Column(db.String(10))
	mode_of_payment = db.Column(db.String(20))
	category = db.Column(db.String(20), default="revenue")
	student_id = db.Column(db.String(10), db.ForeignKey('student.id'))#Here we reference the table name

	def __repr__(self):
		return f'User: {self.student_id}'


class ETLIncome(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	amount = db.Column(db.Integer)
	tx_id = db.Column(db.String(16))
	semester = db.Column(db.String(10), nullable = False)
	mode_of_payment = db.Column(db.String(20))
	category = db.Column(db.String(20), default="revenue")
	student_id = db.Column(db.String(10), db.ForeignKey('student.id'))#Here we reference the table name

	def __repr__(self):
		return f'User: {self.student_id}'


class StudentPayments(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	etl_amount = db.Column(db.Integer)
	pta_amount = db.Column(db.Integer)
	amount = db.Column(db.Integer)
	tx_id = db.Column(db.String(16))
	semester = db.Column(db.String(10), nullable = False)
	mode_of_payment = db.Column(db.String(20))
	category = db.Column(db.String(20), default="revenue")
	student_id = db.Column(db.String(10), db.ForeignKey('student.id'))#Here we reference the table name

	def __repr__(self):
		return f'User: {self.student_id}'

class Expenses(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	item = db.Column(db.String(120))
	purchase_date = db.Column(db.DateTime)
	purpose = db.Column(db.String(120))
	quantity = db.Column(db.Integer)
	unitcost = db.Column(db.Integer)
	totalcost = db.Column(db.Integer)
	elt_expense = db.Column(db.Integer)
	pta_expense = db.Column(db.Integer)
	semester = db.Column(db.String(100))

	def __repr__(self):
		return f'User: {self.item}'

class PTAExpenses(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	item = db.Column(db.String(120))
	purchase_date = db.Column(db.DateTime)
	purpose = db.Column(db.String(120))
	quantity = db.Column(db.Integer)
	unitcost = db.Column(db.Integer)
	totalcost = db.Column(db.Integer)
	semester = db.Column(db.String(100))

	def __repr__(self):
		return f'User: {self.item}'


class ETLExpenses(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	item = db.Column(db.String(120))
	purchase_date = db.Column(db.DateTime)
	purpose = db.Column(db.String(120))
	quantity = db.Column(db.Integer)
	unitcost = db.Column(db.Integer)
	totalcost = db.Column(db.Integer)
	semester = db.Column(db.String(100))

	def __repr__(self):
		return f'User: {self.item}'


class CashBook(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	details = db.Column(db.String(120), default = "Student payments")
	etl = db.Column(db.Integer)
	pta = db.Column(db.Integer)
	amount = db.Column(db.Integer, nullable=False)
	category = db.Column(db.String(100), nullable = False)
	semester = db.Column(db.String(100), nullable = False)
	balance = db.Column(db.Integer, nullable=False)
	expense_id = db.Column(db.Integer)
	income_id = db.Column(db.Integer)

	def __repr__(self):
		return f'User: {self.details}'


class ETLCashBook(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	details = db.Column(db.String(120), default = "ETL Income")
	amount = db.Column(db.Integer)
	category = db.Column(db.String(100))
	semester = db.Column(db.String(100))
	balance = db.Column(db.Integer)
	expense_id = db.Column(db.Integer)
	income_id = db.Column(db.Integer)

	def __repr__(self):
		return f'User: {self.details}'

class PTACashBook(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	details = db.Column(db.String(120), default = "PTA Income")
	amount = db.Column(db.Integer)
	category = db.Column(db.String(100))
	semester = db.Column(db.String(100))
	balance = db.Column(db.Integer)
	expense_id = db.Column(db.Integer)
	income_id = db.Column(db.Integer)

	def __repr__(self):
		return f'User: {self.details}'


class Charges(db.Model):
	__bind_key__ = "kpasec"
	id = db.Column(db.Integer, primary_key=True)
	begin_date = db.Column(db.DateTime)
	end_date = db.Column(db.DateTime)
	etl = db.Column(db.Integer, unique=False, nullable=False)
	pta = db.Column(db.Integer, unique=False, nullable=False)
	total = db.Column(db.Integer, unique=False, nullable=False)
	semester = db.Column(db.String(10), nullable = False)

	def __repr__(self):
		return f'User: {self.total}'




current_sem = Charges.query.all()[-1].semester




#Archives

class ArchivesStudentPayments(db.Model):
	__tablename__ = "archivesstudentpayments"
	__bind_key__ = "kpasecarchives"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	etl_amount = db.Column(db.Integer)
	pta_amount = db.Column(db.Integer)
	amount = db.Column(db.Integer)
	tx_id = db.Column(db.String(16))
	semester = db.Column(db.String(10), nullable = False)
	mode_of_payment = db.Column(db.String(20))
	category = db.Column(db.String(20), default="revenue")
	student_id = db.Column(db.String(10), db.ForeignKey('archivestudent.id'))#Here we reference the table name

	def __repr__(self):
		return f'User: {self.student_id}'


class ArchivesETLIncome(db.Model):
	__tablename__ = "archivesetlincome"
	__bind_key__ = "kpasecarchives"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	amount = db.Column(db.Integer)
	tx_id = db.Column(db.String(16))
	semester = db.Column(db.String(10), nullable = False)
	mode_of_payment = db.Column(db.String(20))
	category = db.Column(db.String(20), default="revenue")
	student_id = db.Column(db.String(10), db.ForeignKey('archivestudent.id'))#Here we reference the table name

	def __repr__(self):
		return f'User: {self.student_id}'


class ArchivesPTAIncome(db.Model):
	__tablename__ = "archivesptaincome"
	__bind_key__ = "kpasecarchives"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	amount = db.Column(db.Integer)
	tx_id = db.Column(db.String(16))
	semester = db.Column(db.String(10))
	mode_of_payment = db.Column(db.String(20))
	category = db.Column(db.String(20), default="revenue")
	student_id = db.Column(db.String(10), db.ForeignKey('archivestudent.id'))#Here we reference the table name

	def __repr__(self):
		return f'User: {self.student_id}'



class ArchivesStudent(db.Model):
	__tablename__ = "archivestudent"
	__bind_key__ = "kpasecarchives"
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.DateTime, default = datetime.utcnow())
	date_admitted = db.Column(db.DateTime)
	fullname = db.Column(db.String(80), unique=False, nullable=False)
	date_of_birth = db.Column(db.String(10), unique=True)
	class1 = db.Column(db.String(10), unique=False, nullable=False)
	parent_contact = db.Column(db.String(120), nullable=False)
	phone = db.Column(db.String(12))
	id_number = db.Column(db.String(120), unique=True, nullable=False)
	status = db.Column(db.Boolean, default=True)
	pta = db.relationship('ArchivesPTAIncome', backref='pta_payer', lazy=True)#Here we reference the class
	etl = db.relationship('ArchivesETLIncome', backref='etl_payer', lazy=True)
	payer = db.relationship('ArchivesStudentPayments', backref='payer', lazy=True)



def move_to_archives(std_id):
	std = Student.get_or_404(std_id)
	arch = ArchivesStudent(id=std.id, phone=std.phone, date=std.date, fullname=std.fullname, date_of_birth=std.date_of_birth,
		class1=student.class1, parent_contact=std.parent_contact, id_number=std.id_number, status=False)
	

	pmt = StudentPayments.query.filter_by(student_id=stud_id_id).first()
	etl = PTAIncome.query.filter_by(student_id=stud_id_id).first()
	pta = ETLIncome.query.filter_by(student_id=stud_id_id).first()

	ptarch = ArchivesPTAIncome(amount=pta.amount, tx_id=pta.tx_id, semester=pta.semester, mode_of_payment=pat.mode_of_payment, category=pta.category, student_id=pta.student_id)
	etlarch = ArchivesETLIncome(amount=etl.amount, tx_id=etl.tx_id, semester=etl.semester, mode_of_payment=etl.mode_of_payment, category=etl.category, student_id=etl.student_id)
	pamtach = ArchivesStudentPayments(etl_amount=pmt.etl_amount, pta_amount=pmt.pta_amount, amount=pmt.amount, tx_id=pmt.tx_id, semester=pmt.semester, mode_of_payment=pmt.mode_of_payment,
	 category=pmt.category, student_id=pmt.student_id)

	db.session.add(arch)
	db.session.add(ptarch)
	db.session.add(etlarch)
	db.session.add(pamtach)
	db.delete(std)
	db.delete(pmt)
	db.delete(etl)
	db.delete(pta)
	db.session.commit()



def obtain_cash_book_balances(database):
	cash = db.session.query(database).order_by(database.date)
	obj = [i.amount if i.category =="revenue" else -1*i.amount for i in cash]
	cum = cumsum(obj)
	if cum.size < 1:
		return 0
	if cum.size >= 1:
		return cum[-1]




class MyModelView(ModelView):
	def is_accessible(self):
		if current_user.is_authenticated:
			return True
		else:
			return False


admin = Admin(app, template_mode='bootstrap4')
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Student, db.session))
admin.add_view(MyModelView(StudentPayments, db.session))
admin.add_view(MyModelView(Expenses, db.session))
admin.add_view(MyModelView(CashBook, db.session))
admin.add_view(MyModelView(PTAIncome, db.session))

if __name__ == '__main__':
	app.run(debug = False)





#enctype in forms
#securities
#flask admin
#rss feed
