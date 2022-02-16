@app.route("/register_client", methods = ['GET', 'POST'])
def register_client():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = ClientSignUpForm()
	if form.validate_on_submit():
		if request.method == "POST":
			company_name = form.data['company_name']
			email = form.data['email']
			password = form.data['password']
			hash_password = bcrypt.generate_password_hash(password).decode("utf-8")
			data = Client(company_name=company_name, email=email, password=hash_password)
			db.session.add(data)
			db.session.commit()
		flash(f"Account successfully created for {form.username.data}", "success")
		return redirect(url_for("login"))
	return render_template("register_client.html", form=form)

@app.route("/client_login", methods = ['GET', 'POST'])
@login_required
def client_login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = ClientLogInForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user and bcrypt.check_password_hash(user.password, form.password.data):
			login_user(user, remember=form.remember.data)
			next_page = request.args.get('next')
			return redirect(next_page) if next_page else redirect(url_for('data_entry_clerk'))
		else:
			flash("Login unsuccessful, please try again", "danger")
	return render_template("client_login.html", form=form)



@app.route("/reports")
@login_required
def reports():
	form = ReportsForm()
	report = request.args.get("report")
	start = request.args.get("start")
	end = request.args.get("end")
	filter1 = request.args.get("filter_by")
	
	if report == "Cash Book":
		end1 = dt.datetime.strptime(end, "%Y-%m-%d").date() + dt.timedelta(1)
		if filter1 != "ETL & PTA Levy":
			cash_filter = CashBook.query.filter(CashBook.date <= end1).filter(CashBook.date >= start).filter(CashBook.details==filter1).all()
			cash_obj1, cash_cums, sum1, sum2 = extract_cash_book_data(cash_obj=cash_filter)
			return cash_book_template(cash_data=cash_obj1, cash_cums=cash_cums, sum1=sum1, sum2=sum2, start_date=start, end_date=end)
		else:
			cash_filter = CashBook.query.filter(CashBook.date <= end1).filter(CashBook.date >= start).all()
			cash_obj1, cash_cums, sum1, sum2 = extract_cash_book_data(cash_obj=cash_filter)
			return cash_book_template(cash_data=cash_obj1, cash_cums=cash_cums, sum1=sum1, sum2=sum2, start_date=start, end_date=end)
	if report == "Income & Expenditure":
		end1 = dt.datetime.strptime(end, "%Y-%m-%d").date() + dt.timedelta(1)
		inc_by_date = StudentPayments.query.filter(StudentPayments.date <= end1).filter(StudentPayments.date >= start)
		exp_by_date = Expenses.query.filter(Expenses.date <= end1).filter(Expenses.date >= start)
		inc_obj, inc_cum, exp_obj, exp_cum, total = extract_income_and_expense_data(inc_obj=inc_by_date, exp_obj=exp_by_date)
		return income_expenditure_template(income=list(inc_obj), inc_cum=inc_cum, expense=exp_obj, exp_cum=exp_cum, total=total, start_date=start, end_date=end)
	if report == "Income Statement":
		end1 = dt.datetime.strptime(end, "%Y-%m-%d").date() + dt.timedelta(1)
		if filter1 != "ETL & PTA Levy":
			inc_by_date = StudentPayments.query.filter(StudentPayments.date <= end1).filter(StudentPayments.date >= start).filter(StudentPayments.category == filter1).all()
			income, inc_cum = extract_income_data(inc_obj = inc_by_date)
			return income_template(income=income, inc_cum=inc_cum, start_date=start, end_date=end1)
		else:
			inc_by_date = StudentPayments.query.filter(StudentPayments.date <= end1).filter(StudentPayments.date >= start).all()
			income, inc_cum = extract_income_data(inc_obj = inc_by_date)
			return income_template(income=income, inc_cum=inc_cum, start_date=start, end_date=end)
	if report == "Expenditure Statement":
		end1 = dt.datetime.strptime(end, "%Y-%m-%d").date() + dt.timedelta(1)
		exp_by_date = Expenses.query.filter(Expenses.date <= end1).filter(Expenses.date >= start).all()
		expense, exp_cum = extract_expense_data(exp_obj=exp_by_date)
		return expenditure_template(expense=expense, exp_cum=exp_cum, start_date=start, end_date=end)
	return render_template("reports.html", form=form)



@app.route("/download")
def download():
	file = "downloads/file1.jpg"
	return send_file(file, as_attachment = True)
